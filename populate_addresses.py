#!/usr/bin/env python3
"""
Populate formatted_address field in database from local JSON file.

This script reads the all_tours.json file and updates the database
with formatted_address data for each site.

Usage:
    # Dry run (shows what would change without making changes)
    python populate_addresses.py --dry-run

    # Actually update the database
    python populate_addresses.py
"""

import json
import os
import sys
import argparse
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """Get database connection from environment variables."""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to database: {e}")
        sys.exit(1)


def load_json_tours():
    """Load tours from the local JSON file."""
    # Try multiple possible locations for the JSON file
    script_dir = Path(__file__).parent
    possible_paths = [
        script_dir / 'all_tours.json',  # Same directory as script (when copied to container)
        script_dir / '..' / '..' / 'ios' / 'Voyana2' / 'Models' / 'all_tours.json',  # Original location
    ]

    json_path = None
    for path in possible_paths:
        if path.exists():
            json_path = path
            break

    if not json_path:
        print(f"❌ ERROR: JSON file not found in any of these locations:")
        for path in possible_paths:
            print(f"   - {path}")
        sys.exit(1)

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            tours = json.load(f)
        print(f"✅ Loaded {len(tours)} tours from JSON")
        return tours
    except Exception as e:
        print(f"❌ ERROR: Failed to load JSON: {e}")
        sys.exit(1)


def extract_sites_from_tours(tours):
    """Extract all sites with their formatted addresses from tours."""
    sites = {}

    for tour in tours:
        tour_name = tour.get('name', 'Unknown')

        for site in tour.get('sites', []):
            site_id = site.get('id')
            formatted_address = site.get('formatted_address')
            title = site.get('title', 'Unknown')

            if site_id:
                # Store site info (may have duplicates across tours, that's ok)
                sites[site_id] = {
                    'id': site_id,
                    'title': title,
                    'formatted_address': formatted_address,
                    'tour': tour_name
                }

    print(f"✅ Extracted {len(sites)} unique sites from tours")
    return sites


def get_current_addresses(conn):
    """Get current formatted_address state from database."""
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
            SELECT id, title, formatted_address
            FROM sites
        """)

        db_sites = {}
        for row in cursor.fetchall():
            db_sites[str(row['id'])] = {
                'title': row['title'],
                'formatted_address': row['formatted_address']
            }

        print(f"✅ Found {len(db_sites)} sites in database")
        return db_sites
    finally:
        cursor.close()


def update_addresses(conn, sites_to_update, dry_run=False):
    """Update formatted_address in database."""
    cursor = conn.cursor()

    updated_count = 0
    missing_count = 0
    already_set_count = 0

    try:
        for site_id, site_data in sites_to_update.items():
            new_address = site_data['formatted_address']
            title = site_data['title']

            if not new_address:
                missing_count += 1
                print(f"⚠️  Skipping '{title}' (no address in JSON)")
                continue

            if dry_run:
                print(f"🔍 Would update '{title}': {new_address}")
                updated_count += 1
            else:
                try:
                    cursor.execute("""
                        UPDATE sites
                        SET formatted_address = %s
                        WHERE id = %s::uuid
                    """, (new_address, site_id))

                    if cursor.rowcount > 0:
                        updated_count += 1
                        print(f"✅ Updated '{title}': {new_address}")
                    else:
                        print(f"⚠️  Site '{title}' not found in database (ID: {site_id})")
                except Exception as e:
                    print(f"❌ Failed to update '{title}': {e}")

        if not dry_run:
            conn.commit()
            print(f"\n✅ Changes committed to database")

        return {
            'updated': updated_count,
            'missing': missing_count,
            'already_set': already_set_count
        }
    finally:
        cursor.close()


def main():
    parser = argparse.ArgumentParser(description='Populate formatted_address from JSON')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would change without making changes')
    args = parser.parse_args()

    print("=" * 60)
    print("Populate Formatted Addresses from JSON")
    print("=" * 60)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")

    # Load JSON data
    tours = load_json_tours()
    json_sites = extract_sites_from_tours(tours)

    # Connect to database
    print("\n📊 Connecting to database...")
    conn = get_db_connection()

    try:
        # Get current state
        db_sites = get_current_addresses(conn)

        # Find sites that need updating
        print("\n🔍 Analyzing what needs updating...")
        sites_to_update = {}
        sites_already_set = []

        for site_id, json_data in json_sites.items():
            db_data = db_sites.get(site_id)

            if not db_data:
                # Site in JSON but not in database
                print(f"⚠️  Site '{json_data['title']}' in JSON but not in database")
                continue

            # Check if address needs updating
            if db_data['formatted_address']:
                # Already has an address
                sites_already_set.append(json_data['title'])
            else:
                # Needs update
                sites_to_update[site_id] = json_data

        print(f"\n📊 Summary:")
        print(f"   Sites with addresses already set: {len(sites_already_set)}")
        print(f"   Sites needing updates: {len(sites_to_update)}")

        if not sites_to_update:
            print("\n✅ All sites already have addresses! Nothing to do.")
            return

        # Update addresses
        print(f"\n{'🔍 Would update' if args.dry_run else '📝 Updating'} {len(sites_to_update)} sites...\n")
        results = update_addresses(conn, sites_to_update, dry_run=args.dry_run)

        # Final summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"✅ Updated: {results['updated']}")
        print(f"⚠️  Missing address in JSON: {results['missing']}")
        print(f"ℹ️  Already had addresses: {len(sites_already_set)}")

        if args.dry_run:
            print("\n🔍 This was a dry run. Run without --dry-run to apply changes.")
        else:
            print("\n✅ All changes have been applied!")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
