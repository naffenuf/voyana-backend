"""
CLI commands for entrance correction and route planning.

Both commands are dry-run by default: they fetch from Google, cache raw
results in S3 (so interrupted runs resume and apply never re-fetches), and
upload a reviewable proposal. Nothing touches the database without --apply.

Intended to run in the Render shell, where DATABASE_URL and GOOGLE_API_KEY
are the production values:

    flask update-entrances --limit 5          # spot-check
    flask update-entrances                    # full dry run -> proposal CSV
    flask update-entrances --apply            # write reviewed results

    flask plan-routes --limit 5               # spot-check
    flask plan-routes                         # full dry run -> proposal
    flask plan-routes --apply                 # rewrite display_order

Order matters: run update-entrances --apply before plan-routes, so walking
distances are measured between the corrected coordinates.
"""
import csv
import io
import json
from datetime import datetime, timezone

import click
from flask import current_app

S3_PREFIX = 'route-planning'
ENTRANCE_CACHE_KEY = f'{S3_PREFIX}/entrance_results.json'
ENTRANCE_PROPOSAL_KEY = f'{S3_PREFIX}/entrance_proposal.csv'
TRANSIT_CACHE_KEY = f'{S3_PREFIX}/transit_cache.json'
MATRIX_CACHE_KEY = f'{S3_PREFIX}/matrix_cache.json'
ROUTE_PROPOSAL_KEY = f'{S3_PREFIX}/route_proposal.json'
ROUTE_PROPOSAL_CSV_KEY = f'{S3_PREFIX}/route_proposal.csv'

# Upload the entrance cache after this many new fetches, so a dropped shell
# session loses at most one batch.
CACHE_FLUSH_EVERY = 25

# Entrance shifts above this (metres) are not auto-applied; they are usually
# legitimately large places, but deserve a human look.
DEFAULT_MAX_SHIFT_M = 150.0


# ---------------------------------------------------------------------------
# S3 helpers
# ---------------------------------------------------------------------------

def _bucket():
    return current_app.config['AWS_S3_BUCKET_NAME']


def _s3_read_json(key, default):
    from app.services.s3_service import get_s3_client
    try:
        obj = get_s3_client().get_object(Bucket=_bucket(), Key=key)
        return json.loads(obj['Body'].read())
    except Exception:
        return default


def _s3_write(key, body, content_type):
    """
    Upload a proposal artefact and return a temporary download link.

    Returns a presigned HTTPS URL (valid 24h) so the file can be opened from a
    browser or curl, rather than an s3:// path needing separate credentials.
    """
    from app.services.s3_service import get_s3_client, generate_presigned_url
    get_s3_client().put_object(
        Bucket=_bucket(), Key=key, Body=body.encode('utf-8'),
        ContentType=content_type,
    )
    region = current_app.config['AWS_S3_REGION']
    object_url = f'https://{_bucket()}.s3.{region}.amazonaws.com/{key}'
    return generate_presigned_url(object_url, expires_in=86400) or object_url


def _s3_write_json(key, data):
    return _s3_write(key, json.dumps(data, indent=1), 'application/json')


def _confirm_database(yes):
    """Show which database is about to be written and ask before continuing."""
    uri = current_app.config.get('SQLALCHEMY_DATABASE_URI') or ''
    host = uri.split('@')[-1].split('/')[0] if '@' in uri else uri
    print(f'About to WRITE to database host: {host}')
    if not yes and not click.confirm('Continue?'):
        raise click.Abort()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_route_planning_commands(app):

    # -----------------------------------------------------------------------
    # check-google-apis
    # -----------------------------------------------------------------------

    @app.cli.command('check-google-apis')
    def check_google_apis():
        """Probe the Google services the planning commands depend on."""
        import hashlib
        import requests as rq
        from app.models.site import Site
        from app.services import entrance_service, route_planner

        api_key = current_app.config.get('GOOGLE_API_KEY')
        if not api_key:
            print('GOOGLE_API_KEY is not configured.')
            return
        digest = hashlib.sha256(api_key.encode()).hexdigest()[:12]
        print(f'Key: {api_key[:6]}...{api_key[-4:]} (sha256:{digest})\n')

        point = (40.7145, -73.9982)  # Chinatown; any dense area works

        def report(label, fn):
            try:
                fn()
                print(f'  OK       {label}')
            except (route_planner.GoogleServiceBlocked,
                    entrance_service.EntranceLookupBlocked) as e:
                print(f'  BLOCKED  {label}\n           {e}')
            except rq.HTTPError as e:
                print(f'  ERROR    {label}: HTTP {e.response.status_code} '
                      f'{e.response.text[:150]}')
            except Exception as e:
                print(f'  ERROR    {label}: {e}')

        report('Places API (New) searchNearby      [plan-routes]',
               lambda: route_planner.find_transit_stations(api_key, [point]))
        def probe_matrix():
            # Returns None rather than raising on non-403 failures, so an
            # empty result must be reported as a failure, not as success.
            if route_planner.walking_distance_matrix(
                    api_key, [point, (40.7180, -73.9900)]) is None:
                raise RuntimeError('request failed (see logged error above)')

        report('Routes API v2 computeRouteMatrix   [plan-routes]', probe_matrix)

        site = Site.query.filter(Site.place_id.isnot(None)).first()
        place_id = site.place_id if site else 'ChIJqwvF8CZawokRwi6ijQhRGD0'
        report('Geocoding v4 SearchDestinations    [update-entrances]',
               lambda: entrance_service.fetch_destination(api_key, place_id))

        print('\nAnything BLOCKED needs the named API enabled for the project '
              "and added to the key's API restrictions in Cloud Console.")

    # -----------------------------------------------------------------------
    # update-entrances
    # -----------------------------------------------------------------------

    @app.cli.command('update-entrances')
    @click.option('--apply', 'apply_', is_flag=True,
                  help='Write cached results to the database (no API calls).')
    @click.option('--limit', type=int, default=None,
                  help='Only process this many sites (spot-checking).')
    @click.option('--max-shift', type=float, default=DEFAULT_MAX_SHIFT_M,
                  help='Auto-apply threshold in metres; larger shifts are '
                       'skipped unless passed via --site-id.')
    @click.option('--site-id', 'site_ids', multiple=True,
                  help='Force-apply these site IDs regardless of shift.')
    @click.option('--refresh', is_flag=True,
                  help='Re-fetch sites even when already cached.')
    @click.option('--yes', is_flag=True, help='Skip the write confirmation.')
    def update_entrances(apply_, limit, max_shift, site_ids, refresh, yes):
        """Look up building entrances for sites (dry run by default)."""
        from app.models.site import Site
        from app.services.route_planner import haversine
        from app.services import entrance_service

        cache = _s3_read_json(ENTRANCE_CACHE_KEY, {})
        sites = (Site.query.filter(Site.place_id.isnot(None))
                 .order_by(Site.title).all())
        skipped_no_place_id = Site.query.filter(Site.place_id.is_(None)).count()
        if limit:
            sites = sites[:limit]

        if apply_:
            _apply_entrances(sites, cache, max_shift, set(site_ids), yes)
            return

        # --- Fetch phase (dry run) ---
        api_key = current_app.config.get('GOOGLE_API_KEY')
        if not api_key:
            print('GOOGLE_API_KEY is not configured; aborting.')
            return

        fetched = 0
        since_flush = 0
        for site in sites:
            if site.place_id in cache and not refresh:
                continue
            try:
                raw = entrance_service.fetch_destination(api_key, site.place_id)
            except entrance_service.EntranceLookupBlocked as e:
                print(f'\nABORTED: {e}')
                break
            except Exception as e:
                print(f'  fetch failed for {site.title}: {e}')
                cache[site.place_id] = {'status': 'error', 'error': str(e)}
                continue

            entrance = entrance_service.extract_entrance(
                raw, site.place_id, (site.latitude, site.longitude))
            if entrance:
                lat, lng, source = entrance
                cache[site.place_id] = {
                    'status': 'ok', 'lat': lat, 'lng': lng, 'source': source,
                }
            else:
                cache[site.place_id] = {'status': 'no_data'}

            fetched += 1
            since_flush += 1
            if since_flush >= CACHE_FLUSH_EVERY:
                _s3_write_json(ENTRANCE_CACHE_KEY, cache)
                since_flush = 0
                print(f'  ...{fetched} fetched (cache flushed)')

        if since_flush:
            _s3_write_json(ENTRANCE_CACHE_KEY, cache)

        # --- Proposal phase ---
        rows = []
        no_data = errors = 0
        for site in sites:
            entry = cache.get(site.place_id)
            if not entry:
                continue
            if entry['status'] == 'no_data':
                no_data += 1
                continue
            if entry['status'] == 'error':
                errors += 1
                continue
            shift = haversine((site.latitude, site.longitude),
                              (entry['lat'], entry['lng']))
            rows.append({
                'site_id': str(site.id),
                'title': site.title,
                'old_lat': site.latitude, 'old_lng': site.longitude,
                'new_lat': entry['lat'], 'new_lng': entry['lng'],
                'source': entry['source'],
                'shift_m': round(shift, 1),
            })
        rows.sort(key=lambda r: -r['shift_m'])

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()) if rows
                                else ['site_id'])
        writer.writeheader()
        writer.writerows(rows)
        url = _s3_write(ENTRANCE_PROPOSAL_KEY, buffer.getvalue(), 'text/csv')

        flagged = [r for r in rows if r['shift_m'] > max_shift]
        print(f'\nSites with place_id: {len(sites)}'
              f'  (fetched this run: {fetched},'
              f' without place_id: {skipped_no_place_id})')
        print(f'Entrance found: {len(rows)}   no data: {no_data}   errors: {errors}')
        print(f'Within {max_shift:.0f}m (auto-applies): {len(rows) - len(flagged)}'
              f'   flagged for review: {len(flagged)}')
        print(f'\nProposal: {url}')
        if rows:
            print(f'\nLargest shifts:')
            for r in rows[:15]:
                print(f"  {r['shift_m']:7.1f}m  {r['source']:22s}  {r['title'][:44]}")
        print('\nDry run only - nothing written. Re-run with --apply to write.')

    def _apply_entrances(sites, cache, max_shift, forced_ids, yes):
        from app import db
        from app.services.route_planner import haversine

        _confirm_database(yes)

        applied = skipped_flagged = no_result = 0
        for site in sites:
            entry = cache.get(site.place_id)
            if not entry or entry['status'] != 'ok':
                no_result += 1
                continue
            shift = haversine((site.latitude, site.longitude),
                              (entry['lat'], entry['lng']))
            if shift > max_shift and str(site.id) not in forced_ids:
                skipped_flagged += 1
                print(f'  SKIPPED ({shift:.0f}m > {max_shift:.0f}m): {site.title}')
                continue
            site.entrance_lat = entry['lat']
            site.entrance_lng = entry['lng']
            site.entrance_source = entry['source']
            applied += 1

        from app import db as _db
        _db.session.commit()
        print(f'\nApplied: {applied}   skipped (flagged): {skipped_flagged}'
              f'   no cached entrance: {no_result}')
        if skipped_flagged:
            print('Apply flagged sites individually with --site-id <id> '
                  'after reviewing the proposal CSV.')

    # -----------------------------------------------------------------------
    # plan-routes
    # -----------------------------------------------------------------------

    @app.cli.command('plan-routes')
    @click.option('--apply', 'apply_', is_flag=True,
                  help='Write the cached proposal to the database.')
    @click.option('--tour-id', 'tour_ids', multiple=True,
                  help='Only these tours (dry run and apply).')
    @click.option('--limit', type=int, default=None,
                  help='Only process this many tours (spot-checking).')
    @click.option('--use-haversine', is_flag=True,
                  help='Preview with straight-line distances (no billable '
                       'Distance Matrix calls; do not apply from this).')
    @click.option('--refresh', is_flag=True,
                  help='Ignore cached transit/matrix results.')
    @click.option('--yes', is_flag=True, help='Skip the write confirmation.')
    def plan_routes(apply_, tour_ids, limit, use_haversine, refresh, yes):
        """Choose start sites and optimal walking order (dry run by default)."""
        from app.models.tour import Tour

        if apply_:
            _apply_routes(set(tour_ids), yes)
            return

        query = Tour.query.filter(Tour.status == 'published')
        if tour_ids:
            query = Tour.query.filter(Tour.id.in_(tour_ids))
        tours = query.order_by(Tour.name).all()
        if limit:
            tours = tours[:limit]

        proposal = _build_route_proposal(tours, use_haversine, refresh)
        if proposal is None:
            return

        json_url = _s3_write_json(ROUTE_PROPOSAL_KEY, proposal)
        csv_url = _s3_write(ROUTE_PROPOSAL_CSV_KEY,
                            _route_proposal_csv(proposal), 'text/csv')

        changed = [p for p in proposal['tours'] if p['order_changed']]
        print(f"\nTours planned: {len(proposal['tours'])}"
              f'   order changes: {len(changed)}')
        print(f'Proposal: {json_url}')
        print(f'Summary:  {csv_url}')
        print(f"\n{'current_m':>9} {'proposed_m':>10} {'margin%':>8}  start -> tour")
        for p in proposal['tours']:
            mark = '*' if p['order_changed'] else ' '
            margin = (f"{p['runner_up_margin_pct']:.1f}"
                      if p['runner_up_margin_pct'] is not None else '  n/a')
            print(f"{p['current_meters']:9.0f} {p['proposed_meters']:10.0f}"
                  f" {margin:>8} {mark} {p['start_title'][:24]:24s}"
                  f" {p['tour_name'][:38]}")
        if use_haversine:
            print('\nNOTE: straight-line preview. Re-run without '
                  '--use-haversine before applying.')
        print('\nDry run only - nothing written. Re-run with --apply to write.')

    def _build_route_proposal(tours, use_haversine, refresh):
        from app.services import route_planner

        api_key = None
        if not use_haversine:
            api_key = current_app.config.get('GOOGLE_API_KEY')
            if not api_key:
                print('ABORTED: GOOGLE_API_KEY is not configured')
                return None

        transit_cache = _s3_read_json(TRANSIT_CACHE_KEY, {})
        matrix_cache = _s3_read_json(MATRIX_CACHE_KEY, {})
        planned = []

        for tour in tours:
            tour_sites = sorted(tour.tour_sites, key=lambda ts: ts.display_order)
            sites = [ts.site for ts in tour_sites]
            if len(sites) < 3:
                print(f'  skipping (fewer than 3 sites): {tour.name}')
                continue

            # Route between entrances where known, centroids otherwise -
            # the same coordinates the route endpoint will use.
            points = [((s.entrance_lat, s.entrance_lng)
                       if s.entrance_lat is not None else
                       (s.latitude, s.longitude)) for s in sites]
            site_dicts = [{
                'latitude': p[0], 'longitude': p[1],
                'types': s.types, 'user_ratings_total': s.user_ratings_total,
            } for s, p in zip(sites, points)]

            tour_key = str(tour.id)
            coord_key = f'{tour_key}:' + ','.join(
                f'{p[0]:.6f},{p[1]:.6f}' for p in points)

            if api_key:
                try:
                    if tour_key not in transit_cache or refresh:
                        transit_cache[tour_key] = (
                            route_planner.find_transit_stations(api_key, points))
                        _s3_write_json(TRANSIT_CACHE_KEY, transit_cache)
                    stations = transit_cache[tour_key]
                    # JSON round-trips tuples as lists; normalise.
                    for st in stations:
                        st['location'] = tuple(st['location'])

                    if coord_key not in matrix_cache or refresh:
                        matrix = route_planner.walking_distance_matrix(
                            api_key, points)
                        if matrix is None:
                            print(f'  matrix failed, skipping: {tour.name}')
                            continue
                        matrix_cache[coord_key] = matrix
                        _s3_write_json(MATRIX_CACHE_KEY, matrix_cache)
                    matrix = matrix_cache[coord_key]
                except route_planner.GoogleServiceBlocked as e:
                    print(f'\nABORTED: {e}')
                    return None
            else:
                stations = []
                matrix = route_planner.haversine_matrix(points)

            plan = route_planner.plan_tour(site_dicts, stations, matrix)
            order = plan['order']

            planned.append({
                'tour_id': tour_key,
                'tour_name': tour.name,
                'used_walking_distances': api_key is not None,
                'station_count': len(stations),
                'start_title': sites[plan['start_index']].title,
                'start_reasons': plan['scores'][plan['start_index']],
                'current_order': [{'site_id': str(s.id), 'title': s.title}
                                  for s in sites],
                'proposed_order': [{'site_id': str(sites[i].id),
                                    'title': sites[i].title} for i in order],
                'order_changed': order != list(range(len(sites))),
                'current_meters': plan['current_meters'],
                'proposed_meters': plan['proposed_meters'],
                'runner_up_margin_pct': plan['runner_up_margin_pct'],
            })

        return {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'tours': planned,
        }

    def _route_proposal_csv(proposal):
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['tour', 'start', 'current_m', 'proposed_m',
                         'margin_pct', 'order_changed', 'proposed_order'])
        for p in proposal['tours']:
            writer.writerow([
                p['tour_name'], p['start_title'], p['current_meters'],
                p['proposed_meters'], p['runner_up_margin_pct'],
                p['order_changed'],
                ' -> '.join(s['title'] for s in p['proposed_order']),
            ])
        return buffer.getvalue()

    def _apply_routes(only_tour_ids, yes):
        from app import db
        from app.models.tour import Tour, TourSite
        from app.services.tour_calculator import calculate_tour_metrics

        proposal = _s3_read_json(ROUTE_PROPOSAL_KEY, None)
        if not proposal:
            print('No proposal found in S3. Run the dry run first.')
            return
        print(f"Applying proposal generated at {proposal['generated_at']}")
        if any(not p['used_walking_distances'] for p in proposal['tours']):
            print('REFUSING: proposal contains straight-line preview results. '
                  'Re-run the dry run without --use-haversine.')
            return

        _confirm_database(yes)

        applied = skipped = 0
        for p in proposal['tours']:
            if only_tour_ids and p['tour_id'] not in only_tour_ids:
                continue
            tour = Tour.query.get(p['tour_id'])
            if not tour:
                print(f"  gone, skipping: {p['tour_name']}")
                skipped += 1
                continue

            tour_sites = {str(ts.site_id): ts for ts in tour.tour_sites}
            proposed_ids = [s['site_id'] for s in p['proposed_order']]
            if set(tour_sites) != set(proposed_ids):
                print(f"  sites changed since proposal, skipping: {p['tour_name']}")
                skipped += 1
                continue

            for position, site_id in enumerate(proposed_ids, start=1):
                tour_sites[site_id].display_order = position
            tour.is_ordered = True

            db.session.flush()
            db.session.expire(tour, ['tour_sites'])
            distance, duration = calculate_tour_metrics(tour)
            tour.distance_meters = distance
            tour.duration_minutes = duration
            applied += 1
            print(f"  applied: {p['tour_name']} (start: {p['start_title']})")

        db.session.commit()
        print(f'\nApplied: {applied}   skipped: {skipped}')
