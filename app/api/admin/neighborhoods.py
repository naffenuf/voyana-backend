"""
Admin neighborhood description management endpoints.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy import select, distinct
from app import db
from app.models.neighborhood import NeighborhoodDescription
from app.models.tour import Tour
from app.models.site import Site
from app.utils.admin_required import admin_required

admin_neighborhoods_bp = Blueprint('admin_neighborhoods', __name__)


@admin_neighborhoods_bp.route('/all-from-tours', methods=['GET'])
@jwt_required()
@admin_required()
def get_all_neighborhoods_from_tours():
    """
    Get all unique city/neighborhood combinations from tours (admin only).

    Returns:
        {
            "neighborhoods": [
                {
                    "city": "New York",
                    "neighborhood": "Chelsea",
                    "tourCount": 5
                },
                ...
            ],
            "total": 10
        }
    """
    try:
        # Get all distinct city/neighborhood from tours with counts
        tour_neighborhoods = db.session.query(
            Tour.city,
            Tour.neighborhood,
            db.func.count(Tour.id).label('tour_count')
        ).filter(
            Tour.city.isnot(None),
            Tour.neighborhood.isnot(None)
        ).group_by(
            Tour.city,
            Tour.neighborhood
        ).all()

        # Build simple result list
        result = []
        for city, neighborhood, tour_count in tour_neighborhoods:
            result.append({
                'city': city,
                'neighborhood': neighborhood,
                'tourCount': tour_count
            })

        # Sort by city, then neighborhood
        result.sort(key=lambda x: (x['city'], x['neighborhood']))

        return jsonify({'neighborhoods': result, 'total': len(result)}), 200

    except Exception as e:
        current_app.logger.error(f'Error getting neighborhoods from tours: {e}')
        return jsonify({'error': 'Failed to get neighborhoods'}), 500


@admin_neighborhoods_bp.route('', methods=['GET'])
@jwt_required()
@admin_required()
def list_neighborhoods():
    """
    List all neighborhood descriptions (admin only).

    Query params:
        - city: Filter by city
        - neighborhood: Filter by neighborhood (partial match)
        - limit: Number of results (default: 100)
        - offset: Offset for pagination (default: 0)

    Returns:
        {
            "neighborhoods": [...],
            "total": count,
            "limit": limit,
            "offset": offset
        }
    """
    # Get query params
    city = request.args.get('city', '').strip()
    neighborhood = request.args.get('neighborhood', '').strip()
    limit = min(request.args.get('limit', 100, type=int), 500)
    offset = request.args.get('offset', 0, type=int)

    # Build query
    query = NeighborhoodDescription.query

    # Apply filters
    if city:
        query = query.filter(NeighborhoodDescription.city.ilike(f'%{city}%'))
    if neighborhood:
        query = query.filter(NeighborhoodDescription.neighborhood.ilike(f'%{neighborhood}%'))

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    neighborhoods = query.order_by(
        NeighborhoodDescription.city,
        NeighborhoodDescription.neighborhood
    ).limit(limit).offset(offset).all()

    return jsonify({
        'neighborhoods': [n.to_dict() for n in neighborhoods],
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200


@admin_neighborhoods_bp.route('/<int:neighborhood_id>', methods=['GET'])
@jwt_required()
@admin_required()
def get_neighborhood(neighborhood_id):
    """Get a specific neighborhood description by ID (admin only)."""
    neighborhood = NeighborhoodDescription.query.get(neighborhood_id)

    if not neighborhood:
        return jsonify({'error': 'Neighborhood description not found'}), 404

    return jsonify(neighborhood.to_dict()), 200


@admin_neighborhoods_bp.route('', methods=['POST'])
@jwt_required()
@admin_required()
def create_neighborhood():
    """
    Create a new neighborhood description (admin only).

    Request body:
        {
            "city": "New York",
            "neighborhood": "Chinatown",
            "description": "Historic neighborhood known for..."
        }
    """
    data = request.get_json()

    # Validate required fields (description is optional)
    if not data or not all(k in data for k in ['city', 'neighborhood']):
        return jsonify({'error': 'Missing required fields: city, neighborhood'}), 400

    city = data['city'].strip()
    neighborhood = data['neighborhood'].strip()
    description = data.get('description', '').strip()

    if not city or not neighborhood:
        return jsonify({'error': 'City and neighborhood cannot be empty'}), 400

    # Check for duplicates in NeighborhoodDescription table
    # Note: It's OK if tours have this city/neighborhood combo - we're just adding the description
    existing = NeighborhoodDescription.query.filter_by(
        city=city,
        neighborhood=neighborhood
    ).first()

    if existing:
        return jsonify({'error': f'Neighborhood description for {city}/{neighborhood} already exists'}), 409

    try:
        # Create new neighborhood description
        new_neighborhood = NeighborhoodDescription(
            city=city,
            neighborhood=neighborhood,
            description=description
        )

        db.session.add(new_neighborhood)
        db.session.commit()

        current_app.logger.info(f'Created neighborhood description: {city}/{neighborhood}')
        return jsonify(new_neighborhood.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating neighborhood description: {e}')
        return jsonify({'error': 'Failed to create neighborhood description'}), 500


@admin_neighborhoods_bp.route('/<int:neighborhood_id>', methods=['PUT'])
@jwt_required()
@admin_required()
def update_neighborhood(neighborhood_id):
    """
    Update a neighborhood description with cascading updates (admin only).

    When city or neighborhood name changes, automatically updates all associated
    tours and sites. If the new name conflicts with an existing neighborhood,
    performs a merge operation.

    Request body:
        {
            "city": "New York",
            "neighborhood": "Chinatown",
            "description": "Updated description..."
        }

    Returns:
        {
            "id": 123,
            "city": "New York",
            "neighborhood": "Chinatown",
            "description": "...",
            "toursUpdated": 5,
            "sitesUpdated": 12,
            "merged": false
        }
    """
    neighborhood = NeighborhoodDescription.query.get(neighborhood_id)

    if not neighborhood:
        return jsonify({'error': 'Neighborhood description not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    try:
        # Store original values for cascading update
        old_city = neighborhood.city
        old_neighborhood = neighborhood.neighborhood

        # Parse new values
        new_city = data.get('city', old_city).strip()
        new_neighborhood = data.get('neighborhood', old_neighborhood).strip()
        new_description = data.get('description', neighborhood.description or '').strip()

        # Validate (description is optional)
        if not new_city or not new_neighborhood:
            return jsonify({'error': 'City and neighborhood cannot be empty'}), 400

        # Track statistics
        tours_updated = 0
        sites_updated = 0
        merged = False

        # Check if city or neighborhood is changing
        name_changed = (new_city != old_city or new_neighborhood != old_neighborhood)

        if name_changed:
            # Check for duplicate/merge scenario
            duplicate = NeighborhoodDescription.query.filter(
                NeighborhoodDescription.id != neighborhood_id,
                NeighborhoodDescription.city == new_city,
                NeighborhoodDescription.neighborhood == new_neighborhood
            ).first()

            if duplicate:
                # MERGE SCENARIO
                current_app.logger.info(
                    f'Merging neighborhoods: {old_city}/{old_neighborhood} -> {new_city}/{new_neighborhood} (already exists)'
                )

                # Determine which description to keep
                # Priority: use description from the one that has content, or first if both do
                if duplicate.description and not neighborhood.description:
                    final_description = duplicate.description
                elif neighborhood.description:
                    final_description = neighborhood.description
                    # Update duplicate's description if we're using current one
                    duplicate.description = final_description
                else:
                    # Neither has description (shouldn't happen), use new one
                    final_description = new_description
                    duplicate.description = final_description

                # Update all tours from OLD neighborhood to NEW neighborhood
                tours_result = Tour.query.filter(
                    Tour.city == old_city,
                    Tour.neighborhood == old_neighborhood
                ).update(
                    {Tour.city: new_city, Tour.neighborhood: new_neighborhood},
                    synchronize_session=False
                )
                tours_updated = tours_result

                # Update all sites from OLD neighborhood to NEW neighborhood
                sites_result = Site.query.filter(
                    Site.city == old_city,
                    Site.neighborhood == old_neighborhood
                ).update(
                    {Site.city: new_city, Site.neighborhood: new_neighborhood},
                    synchronize_session=False
                )
                sites_updated = sites_result

                # Delete the OLD neighborhood description (we're merging into duplicate)
                db.session.delete(neighborhood)

                # Commit all changes atomically
                db.session.commit()

                merged = True
                result_neighborhood = duplicate

                current_app.logger.info(
                    f'Merged successfully: {tours_updated} tours, {sites_updated} sites updated. '
                    f'Deleted neighborhood ID {neighborhood_id}, kept ID {duplicate.id}'
                )

            else:
                # NO CONFLICT - Simple cascading update
                current_app.logger.info(
                    f'Cascading update: {old_city}/{old_neighborhood} -> {new_city}/{new_neighborhood}'
                )

                # Update all tours with old city/neighborhood
                tours_result = Tour.query.filter(
                    Tour.city == old_city,
                    Tour.neighborhood == old_neighborhood
                ).update(
                    {Tour.city: new_city, Tour.neighborhood: new_neighborhood},
                    synchronize_session=False
                )
                tours_updated = tours_result

                # Update all sites with old city/neighborhood
                sites_result = Site.query.filter(
                    Site.city == old_city,
                    Site.neighborhood == old_neighborhood
                ).update(
                    {Site.city: new_city, Site.neighborhood: new_neighborhood},
                    synchronize_session=False
                )
                sites_updated = sites_result

                # Update the neighborhood description itself
                neighborhood.city = new_city
                neighborhood.neighborhood = new_neighborhood
                neighborhood.description = new_description

                # Commit all changes atomically
                db.session.commit()

                result_neighborhood = neighborhood

                current_app.logger.info(
                    f'Cascaded successfully: {tours_updated} tours, {sites_updated} sites updated'
                )

        else:
            # Only description changed, no cascading needed
            neighborhood.description = new_description
            db.session.commit()
            result_neighborhood = neighborhood
            current_app.logger.info(f'Updated description only for {neighborhood_id}')

        # Build response with update statistics
        response = result_neighborhood.to_dict()
        response['toursUpdated'] = tours_updated
        response['sitesUpdated'] = sites_updated
        response['merged'] = merged

        return jsonify(response), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error updating neighborhood description {neighborhood_id}: {e}')
        return jsonify({'error': f'Failed to update neighborhood description: {str(e)}'}), 500


@admin_neighborhoods_bp.route('/rename', methods=['PUT'])
@jwt_required()
@admin_required()
def rename_neighborhood():
    """
    Rename/consolidate a neighborhood across all tours and sites (admin only).

    This endpoint ONLY updates tour and site records. It does not create or manage
    neighborhood descriptions.

    Request body:
        {
            "oldCity": "New York",
            "oldNeighborhood": "Chelsea North",
            "newCity": "New York",
            "newNeighborhood": "Chelsea"
        }

    Returns:
        {
            "toursUpdated": 5,
            "sitesUpdated": 12,
            "oldCity": "New York",
            "oldNeighborhood": "Chelsea North",
            "newCity": "New York",
            "newNeighborhood": "Chelsea"
        }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    # Validate required fields
    old_city = data.get('oldCity', '').strip()
    old_neighborhood = data.get('oldNeighborhood', '').strip()
    new_city = data.get('newCity', '').strip()
    new_neighborhood = data.get('newNeighborhood', '').strip()

    if not old_city or not old_neighborhood or not new_city or not new_neighborhood:
        return jsonify({'error': 'oldCity, oldNeighborhood, newCity, and newNeighborhood are required'}), 400

    # Check if no change
    if old_city == new_city and old_neighborhood == new_neighborhood:
        return jsonify({'error': 'Old and new neighborhood are the same'}), 400

    try:
        current_app.logger.info(
            f'Renaming neighborhood: {old_city}/{old_neighborhood} -> {new_city}/{new_neighborhood}'
        )

        # Update all tours
        tours_updated = Tour.query.filter(
            Tour.city == old_city,
            Tour.neighborhood == old_neighborhood
        ).update(
            {Tour.city: new_city, Tour.neighborhood: new_neighborhood},
            synchronize_session=False
        )

        # Update all sites
        sites_updated = Site.query.filter(
            Site.city == old_city,
            Site.neighborhood == old_neighborhood
        ).update(
            {Site.city: new_city, Site.neighborhood: new_neighborhood},
            synchronize_session=False
        )

        db.session.commit()

        current_app.logger.info(
            f'Renamed successfully: {tours_updated} tours, {sites_updated} sites'
        )

        return jsonify({
            'toursUpdated': tours_updated,
            'sitesUpdated': sites_updated,
            'oldCity': old_city,
            'oldNeighborhood': old_neighborhood,
            'newCity': new_city,
            'newNeighborhood': new_neighborhood
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error renaming neighborhood: {e}')
        return jsonify({'error': f'Failed to rename neighborhood: {str(e)}'}), 500


@admin_neighborhoods_bp.route('/<int:neighborhood_id>', methods=['DELETE'])
@jwt_required()
@admin_required()
def delete_neighborhood(neighborhood_id):
    """Delete a neighborhood description (admin only)."""
    neighborhood = NeighborhoodDescription.query.get(neighborhood_id)

    if not neighborhood:
        return jsonify({'error': 'Neighborhood description not found'}), 404

    try:
        city = neighborhood.city
        neighborhood_name = neighborhood.neighborhood

        db.session.delete(neighborhood)
        db.session.commit()

        current_app.logger.info(f'Deleted neighborhood description {neighborhood_id}: {city}/{neighborhood_name}')
        return jsonify({'message': 'Neighborhood description deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting neighborhood description {neighborhood_id}: {e}')
        return jsonify({'error': 'Failed to delete neighborhood description'}), 500
