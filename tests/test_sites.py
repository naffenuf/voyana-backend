"""
Tests for Sites API endpoints.
"""
import pytest
import json
from uuid import uuid4
from app.models.site import Site
from app import db


class TestListSites:
    """Tests for GET /api/sites endpoint."""

    def test_list_sites_default(self, client, test_site):
        """Test listing sites with default parameters."""
        response = client.get('/api/sites')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'sites' in data
        assert 'total' in data
        assert data['total'] >= 1
        assert len(data['sites']) >= 1

    def test_list_sites_search(self, app, client, test_site):
        """Test searching sites by text."""
        response = client.get(f'/api/sites?search={test_site.title}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['sites']) >= 1
        assert any(s['title'] == test_site.title for s in data['sites'])

    def test_list_sites_filter_by_city(self, app, client):
        """Test filtering sites by city."""
        with app.app_context():
            site1 = Site(
                title='NYC Site',
                description='A site in NYC',
                latitude=40.7580,
                longitude=-73.9855,
                city='New York'
            )
            site2 = Site(
                title='SF Site',
                description='A site in SF',
                latitude=37.7749,
                longitude=-122.4194,
                city='San Francisco'
            )
            db.session.add(site1)
            db.session.add(site2)
            db.session.commit()

        response = client.get('/api/sites?city=New York')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert all(s.get('city') == 'New York' for s in data['sites'])

    def test_list_sites_proximity_search(self, app, client):
        """Test proximity search for sites."""
        with app.app_context():
            # Create a site near Times Square
            site = Site(
                title='Times Square Site',
                description='Near Times Square',
                latitude=40.7580,
                longitude=-73.9855
            )
            db.session.add(site)
            db.session.commit()

        # Search within 1km of Times Square
        response = client.get('/api/sites?lat=40.7580&lon=-73.9855&max_distance=1000')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['sites']) >= 1

    def test_list_sites_pagination(self, app, client):
        """Test pagination parameters."""
        with app.app_context():
            # Create multiple sites
            for i in range(5):
                site = Site(
                    title=f'Site {i}',
                    description=f'Description {i}',
                    latitude=40.7 + i * 0.01,
                    longitude=-73.9 + i * 0.01
                )
                db.session.add(site)
            db.session.commit()

        # Test limit
        response = client.get('/api/sites?limit=2')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['sites']) <= 2
        assert data['limit'] == 2

        # Test offset
        response = client.get('/api/sites?limit=2&offset=2')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['offset'] == 2


class TestGetSite:
    """Tests for GET /api/sites/<id> endpoint."""

    def test_get_site_success(self, client, test_site):
        """Test getting a specific site."""
        response = client.get(f'/api/sites/{test_site.id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'site' in data
        site = data['site']
        assert site['id'] == str(test_site.id)
        assert site['title'] == test_site.title
        assert site['description'] == test_site.description

    def test_get_site_not_found(self, client):
        """Test getting non-existent site."""
        fake_id = uuid4()
        response = client.get(f'/api/sites/{fake_id}')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_site_invalid_uuid(self, client):
        """Test getting site with invalid UUID."""
        response = client.get('/api/sites/invalid-uuid')

        assert response.status_code == 404


class TestCreateSite:
    """Tests for POST /api/sites endpoint."""

    def test_create_site_success(self, client, auth_headers):
        """Test creating a site with valid data."""
        response = client.post('/api/sites', headers=auth_headers, json={
            'title': 'New Site',
            'description': 'A new interesting site',
            'latitude': 40.7589,
            'longitude': -73.9851,
            'city': 'New York',
            'neighborhood': 'Times Square'
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'site' in data
        site = data['site']
        assert site['title'] == 'New Site'
        assert 'id' in site

    def test_create_site_requires_auth(self, client):
        """Test that creating a site requires authentication."""
        response = client.post('/api/sites', json={
            'title': 'New Site',
            'latitude': 40.7589,
            'longitude': -73.9851
        })

        assert response.status_code == 401

    def test_create_site_missing_coordinates(self, client, auth_headers):
        """Test creating site without required coordinates."""
        response = client.post('/api/sites', headers=auth_headers, json={
            'title': 'New Site',
            'description': 'Missing coordinates'
        })

        assert response.status_code == 400

    def test_create_site_missing_title(self, client, auth_headers):
        """Test creating site without title."""
        response = client.post('/api/sites', headers=auth_headers, json={
            'latitude': 40.7589,
            'longitude': -73.9851
        })

        assert response.status_code == 400


class TestUpdateSite:
    """Tests for PUT /api/sites/<id> endpoint."""

    def test_update_site_success(self, client, admin_headers, test_site):
        """Test updating a site as admin."""
        response = client.put(f'/api/sites/{test_site.id}', headers=admin_headers, json={
            'title': 'Updated Site Title',
            'description': 'Updated description'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'site' in data
        site = data['site']
        assert site['title'] == 'Updated Site Title'
        assert site['description'] == 'Updated description'

    def test_update_site_requires_admin(self, client, auth_headers, test_site):
        """Test that updating requires admin role."""
        response = client.put(f'/api/sites/{test_site.id}', headers=auth_headers, json={
            'title': 'Updated Title'
        })

        # Should fail if not admin
        assert response.status_code in [403, 401]

    def test_update_site_not_found(self, client, admin_headers):
        """Test updating non-existent site."""
        fake_id = uuid4()
        response = client.put(f'/api/sites/{fake_id}', headers=admin_headers, json={
            'title': 'Updated'
        })

        assert response.status_code == 404


class TestDeleteSite:
    """Tests for DELETE /api/sites/<id> endpoint."""

    def test_delete_site_success(self, app, client, admin_headers):
        """Test deleting a site as admin."""
        with app.app_context():
            site = Site(
                title='Site to Delete',
                description='Will be deleted',
                latitude=40.7589,
                longitude=-73.9851
            )
            db.session.add(site)
            db.session.commit()
            site_id = site.id

        response = client.delete(f'/api/sites/{site_id}', headers=admin_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data

        # Verify site is deleted
        with app.app_context():
            deleted_site = Site.query.get(site_id)
            assert deleted_site is None

    def test_delete_site_requires_admin(self, client, auth_headers, test_site):
        """Test that deleting requires admin role."""
        response = client.delete(f'/api/sites/{test_site.id}', headers=auth_headers)

        # Should fail if not admin
        assert response.status_code in [403, 401]

    def test_delete_site_not_found(self, client, admin_headers):
        """Test deleting non-existent site."""
        fake_id = uuid4()
        response = client.delete(f'/api/sites/{fake_id}', headers=admin_headers)

        assert response.status_code == 404
