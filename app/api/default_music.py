"""
Default Music Tracks API endpoints.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app import db
from app.models.default_music import DefaultMusicTrack
from app.utils.admin_required import admin_required
from app.utils.device_binding import device_binding_required

default_music_bp = Blueprint('default_music', __name__)


@default_music_bp.route('', methods=['GET'])
@device_binding_required()
def list_default_music_tracks():
    """
    List all default music tracks (active only by default).

    Query params:
        - include_inactive: Include inactive tracks (default: false)
    """
    include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'

    query = DefaultMusicTrack.query

    if not include_inactive:
        query = query.filter_by(is_active=True)

    tracks = query.order_by(DefaultMusicTrack.display_order).all()

    return jsonify({
        'tracks': [track.to_dict() for track in tracks]
    }), 200


@default_music_bp.route('/<uuid:track_id>', methods=['GET'])
@device_binding_required()
def get_default_music_track(track_id):
    """Get a single default music track by ID."""
    track = DefaultMusicTrack.query.get(track_id)

    if not track:
        return jsonify({'error': 'Track not found'}), 404

    return jsonify(track.to_dict()), 200


@default_music_bp.route('', methods=['POST'])
@jwt_required()
@admin_required()
def create_default_music_track():
    """
    Create a new default music track (admin only).

    Body:
        - url (required): S3 URL of the music track
        - title (optional): Display title for the track
        - displayOrder (optional): Order in playlist (defaults to last)
    """
    data = request.get_json()

    if not data or not data.get('url'):
        return jsonify({'error': 'URL is required'}), 400

    # Get the next display order if not provided
    display_order = data.get('displayOrder')
    if display_order is None:
        max_order = db.session.query(db.func.max(DefaultMusicTrack.display_order)).scalar()
        display_order = (max_order or 0) + 1

    track = DefaultMusicTrack(
        url=data['url'].strip(),
        title=data.get('title', '').strip() or None,
        display_order=display_order,
        is_active=data.get('isActive', True)
    )

    db.session.add(track)
    db.session.commit()

    current_app.logger.info(f'Created default music track: {track.id}')

    return jsonify(track.to_dict()), 201


@default_music_bp.route('/<uuid:track_id>', methods=['PUT'])
@jwt_required()
@admin_required()
def update_default_music_track(track_id):
    """
    Update a default music track (admin only).

    Body:
        - url (optional): S3 URL of the music track
        - title (optional): Display title for the track
        - displayOrder (optional): Order in playlist
        - isActive (optional): Whether track is active
    """
    track = DefaultMusicTrack.query.get(track_id)

    if not track:
        return jsonify({'error': 'Track not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Update fields
    if 'url' in data:
        url = data['url'].strip()
        if not url:
            return jsonify({'error': 'URL cannot be empty'}), 400
        track.url = url

    if 'title' in data:
        track.title = data['title'].strip() or None

    if 'displayOrder' in data:
        track.display_order = data['displayOrder']

    if 'isActive' in data:
        track.is_active = data['isActive']

    db.session.commit()

    current_app.logger.info(f'Updated default music track: {track.id}')

    return jsonify(track.to_dict()), 200


@default_music_bp.route('/<uuid:track_id>', methods=['DELETE'])
@jwt_required()
@admin_required()
def delete_default_music_track(track_id):
    """Delete a default music track (admin only)."""
    track = DefaultMusicTrack.query.get(track_id)

    if not track:
        return jsonify({'error': 'Track not found'}), 404

    db.session.delete(track)
    db.session.commit()

    current_app.logger.info(f'Deleted default music track: {track_id}')

    return '', 204


@default_music_bp.route('/reorder', methods=['POST'])
@jwt_required()
@admin_required()
def reorder_default_music_tracks():
    """
    Reorder default music tracks (admin only).

    Body:
        - trackIds: Array of track IDs in desired order
    """
    data = request.get_json()

    if not data or not isinstance(data.get('trackIds'), list):
        return jsonify({'error': 'trackIds array is required'}), 400

    track_ids = data['trackIds']

    # Update display order for each track
    for index, track_id in enumerate(track_ids):
        track = DefaultMusicTrack.query.get(track_id)
        if track:
            track.display_order = index + 1

    db.session.commit()

    current_app.logger.info(f'Reordered {len(track_ids)} default music tracks')

    return jsonify({'success': True}), 200
