# CLAUDE.md - Voyana Tours Server

This file provides guidance to Claude Code when working with this server codebase.

## Project Overview

Clean, modern Flask API server for the Voyana mobile tour application. Built with Flask 3.0, SQLAlchemy 2.0, PostgreSQL, and JWT authentication.

## Architecture Principles

### Flask Application Factory Pattern

The app uses the factory pattern (`app/__init__.py:create_app()`):

```python
from app import create_app

app = create_app('development')  # or 'production', 'testing'
```

### Blueprint Organization

API routes are organized into focused blueprints:

```
/auth/*         - Authentication (register, login, refresh)
/api/tours/*    - Tour CRUD operations
/api/sites/*    - Site CRUD operations
/api/media/*    - S3 uploads, presigned URLs
/api/maps/*     - Route optimization, directions
```

### Database Models (SQLAlchemy 2.0)

**Key Models:**
- `User` - User accounts with JWT auth
- `Tour` - Tours with owner, location, status
- `Site` - Points of interest with Google Places data
- `TourSite` - Many-to-many junction table
- `Feedback` - User feedback on tours/sites (ratings, issues, comments, suggestions, photos)
- `AudioCache` - TTS caching by text hash

**Important Patterns:**
- Use `db.session` for all database operations
- Always commit after modifications: `db.session.commit()`
- Use `db.session.rollback()` in exception handlers
- UUIDs for tours/sites, integers for users

### JWT Authentication

**Pattern:**
```python
from flask_jwt_extended import jwt_required, get_jwt_identity

@tours_bp.route('', methods=['POST'])
@jwt_required()
def create_tour():
    user_id = get_jwt_identity()  # Extract user ID from token
    # ... create tour owned by user_id
```

**Token Types:**
- Access token: 1 hour (for API calls)
- Refresh token: 30 days (to get new access tokens)

### Configuration System

Three environments with dedicated config classes:

```python
# Development (default)
FLASK_ENV=development
DATABASE_URL=postgresql://voyana:pass@db:5432/voyana_db

# Production
FLASK_ENV=production
DATABASE_URL=postgresql://user:pass@rds-endpoint/voyana

# Testing
FLASK_ENV=testing
# Uses SQLite in-memory database
```

**Config Priority:**
1. Environment variables (`.env` file)
2. Config class defaults (`app/config/__init__.py`)

### Logging

**Simple stdout logging** (cloud-friendly):
```python
from flask import current_app

current_app.logger.info('Message here')
current_app.logger.error('Error here')
```

All logs go to stdout, captured by Docker/cloud platform.

## Development Workflow

### Local Development with Docker Compose

**Start services:**
```bash
docker-compose up
# App: http://localhost:5000
# DB: localhost:5432
```

**Initialize database:**
```bash
docker-compose exec app flask db upgrade
docker-compose exec app flask seed-dev-data
```

**Run tests:**
```bash
docker-compose exec app pytest
```

**Create migration:**
```bash
docker-compose exec app flask db migrate -m "description"
docker-compose exec app flask db upgrade
```

**Access database:**
```bash
docker-compose exec db psql -U voyana -d voyana_db
```

### Database Migrations (Alembic)

**Always use Flask-Migrate commands:**
```bash
# Create new migration after model changes
flask db migrate -m "Add user_submitted_locations to sites"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

**Never edit models without creating a migration!**

## Key Files & Directories

```
app/
├── __init__.py           # App factory, blueprint registration
├── models/               # SQLAlchemy models
│   ├── user.py          # User, ApiKey, PasswordResetToken
│   ├── tour.py          # Tour, TourSite
│   ├── site.py          # Site with Google Places fields
│   ├── feedback.py      # User feedback
│   └── audio_cache.py   # TTS caching
├── api/                 # API blueprints
│   ├── auth.py          # Authentication endpoints
│   ├── tours.py         # Tour CRUD
│   ├── sites.py         # Site CRUD
│   ├── media.py         # S3 operations
│   └── maps.py          # Route optimization
├── services/            # Business logic (to be created)
│   ├── s3_service.py
│   ├── tts_service.py
│   ├── openai_service.py
│   └── maps_service.py
├── utils/               # Helper functions
└── config/
    ├── __init__.py      # Environment configs
    └── prompts.json     # AI prompt templates
```

## Database Schema

### Tours Table
- `id` (UUID) - Primary key
- `owner_id` (Integer) - Foreign key to users
- `name`, `description` - Tour content
- `city`, `neighborhood` - Location context
- `latitude`, `longitude` - Tour center point (for proximity queries)
- `status` - 'draft', 'live', 'archived'
- `is_public` - Boolean

### Sites Table
- `id` (UUID) - Primary key
- `title`, `description` - Site content
- `latitude`, `longitude` - Required location
- `user_submitted_locations` - Array of [lat, lng] pairs from visitors
- Google Places fields: `place_id`, `formatted_address`, `types`, `phone_number`, `user_ratings_total`
- `google_photo_references` - Array of Google photo URLs

### TourSite Junction
- `tour_id`, `site_id` - Composite primary key
- `display_order` - Integer for site ordering
- `visit_duration_minutes` - Optional

## Common Patterns

### Creating a Protected Endpoint

```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.tour import Tour

tours_bp = Blueprint('tours', __name__)

@tours_bp.route('', methods=['POST'])
@jwt_required()  # Requires valid JWT
def create_tour():
    user_id = get_jwt_identity()
    data = request.get_json()

    # Validate
    if not data or not data.get('name'):
        return jsonify({'error': 'Name required'}), 400

    # Create
    tour = Tour(
        owner_id=user_id,
        name=data['name'],
        status='draft'
    )

    db.session.add(tour)
    db.session.commit()

    return jsonify(tour.to_dict()), 201
```

### Querying with Filters

```python
# Simple query
tour = Tour.query.get(tour_id)

# Filter by fields
tours = Tour.query.filter_by(city='New York', status='live').all()

# Complex filters
from sqlalchemy import and_, or_

tours = Tour.query.filter(
    and_(
        Tour.city == 'New York',
        or_(Tour.status == 'live', Tour.owner_id == user_id)
    )
).all()
```

### Adding to Existing Many-to-Many

```python
from app.models.tour import Tour, TourSite
from app.models.site import Site

tour = Tour.query.get(tour_id)
site = Site.query.get(site_id)

# Add site to tour with order
tour_site = TourSite(
    tour_id=tour.id,
    site_id=site.id,
    display_order=len(tour.tour_sites) + 1
)

db.session.add(tour_site)
db.session.commit()
```

### Error Handling

```python
@tours_bp.route('/<uuid:tour_id>', methods=['GET'])
def get_tour(tour_id):
    tour = Tour.query.get(tour_id)

    if not tour:
        return jsonify({'error': 'Tour not found'}), 404

    # Check access
    if not tour.is_public and tour.owner_id != current_user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        return jsonify(tour.to_dict()), 200
    except Exception as e:
        current_app.logger.error(f'Error getting tour: {e}')
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
```

## Feedback System

### Feedback Types

The feedback system supports five types of user-submitted feedback:

1. **'rating'** - Numerical rating (1-5) for tours
   - Used to calculate tour `average_rating` and `rating_count`
   - Can include optional comment for context
   - Anonymous or authenticated submissions allowed

2. **'issue'** - Problem reports (bugs, incorrect info, safety concerns)
   - Helps identify and fix tour/site data issues
   - Admin review workflow to resolve or dismiss

3. **'comment'** - General user feedback and experiences
   - Qualitative feedback about tours or sites
   - Can inform tour improvements

4. **'suggestion'** - Feature requests and improvement ideas
   - User-driven enhancement suggestions
   - Helps prioritize new features

5. **'photo'** - User-submitted site photos (NEW)
   - Crowdsourced photo improvements for sites
   - Only for sites (not tours)
   - See Photo Feedback Workflow below

### Photo Feedback Workflow

**Purpose:** Enable users to submit better photos for sites than currently displayed, improving site photo quality over time through crowdsourcing.

**User Flow:**
1. User visits a site during a tour
2. User notices the current site photo is poor quality or outdated
3. User takes a photo with their device camera
4. iOS/Android app resizes/optimizes photo before submission (client-side)
5. App submits feedback with:
   ```json
   {
     "siteId": "uuid",
     "feedbackType": "photo",
     "photoData": "base64-encoded-image-string",
     "comment": "Optional description"
   }
   ```

**Backend Storage:**
- `feedback_type` = 'photo'
- `site_id` must be set (NOT `tour_id`)
- `photo_data` contains base64-encoded image data
- `status` starts as 'pending'

**Admin Review Workflow:**
1. Admin dashboard shows pending photo submissions
2. Admin views submitted photo alongside current site photo
3. Admin decides:
   - **Approve**: Replace site's main photo with submitted photo
   - **Resolve**: Keep current photo, mark as reviewed
   - **Dismiss**: Reject (inappropriate, poor quality, etc.)
4. Admin can add notes explaining decision

**Implementation Notes:**
- Client must resize photos BEFORE encoding to base64 (prevents huge payloads)
- Recommended max size: ~800x600 or ~500KB after encoding
- Photo validation happens at API layer (to be implemented)
- Photo decoding/saving to S3 happens during admin approval (to be implemented)

## Testing

### Writing Tests

Create tests in `tests/` directory:

```python
import pytest
from app import create_app, db
from app.models.user import User

@pytest.fixture
def client():
    app = create_app('testing')

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

def test_register(client):
    response = client.post('/auth/register', json={
        'email': 'test@example.com',
        'password': 'password123',
        'name': 'Test User'
    })

    assert response.status_code == 201
    assert 'access_token' in response.json
```

### Running Tests

```bash
# All tests
docker-compose exec app pytest

# Specific file
docker-compose exec app pytest tests/test_auth.py

# With coverage
docker-compose exec app pytest --cov=app
```

## AI Prompts System

Prompts stored in `app/config/prompts.json`:

```json
{
  "site_description_from_coordinates": {
    "model": "gpt-4o",
    "temperature": 0.7,
    "system_prompt": "...",
    "user_prompt_template": "Create description for {site_name} at {latitude}, {longitude}"
  }
}
```

**To add new prompt:**
1. Add entry to `prompts.json`
2. Create service function to render template
3. Call OpenAI API with rendered prompt

## Deployment

### Docker Production Build

```bash
docker build -t voyana-api .
docker run -p 5000:5000 --env-file .env voyana-api
```

### AWS Deployment

**Architecture:**
- **Compute**: ECS Fargate or Elastic Beanstalk
- **Database**: RDS PostgreSQL
- **Storage**: S3 (already configured)

**Environment Variables (Production):**
- `DATABASE_URL` - RDS connection string
- `JWT_SECRET_KEY` - Strong random secret
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- `OPENAI_API_KEY`, `ELEVEN_LABS_API_KEY`, `GOOGLE_API_KEY`

### Health Check

Load balancers should use: `GET /api/health`

Returns:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

## Common Tasks

### Add a New Model

1. Create model file in `app/models/`
2. Import in `app/models/__init__.py`
3. Create migration: `flask db migrate -m "Add model"`
4. Apply migration: `flask db upgrade`

### Add a New Endpoint

1. Add route to appropriate blueprint in `app/api/`
2. Use `@jwt_required()` for protected routes
3. Extract user ID: `user_id = get_jwt_identity()`
4. Validate input, perform operation, return JSON

### Migrate Data from Legacy Server

```bash
# TODO: Create migration script
docker-compose exec app python migrate_legacy_data.py
```

## Important Constraints

- **UUIDs**: Tours and Sites use UUID primary keys (not integers)
- **Coordinates**: Always validate latitude (-90 to 90) and longitude (-180 to 180)
- **Tour Status**: Must be 'draft', 'live', or 'archived'
- **User Roles**: Must be 'admin', 'creator', or 'viewer'
- **Feedback**: Must target either a tour OR a site (not both)

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Yes | Secret for JWT signing |
| `SECRET_KEY` | Yes | Flask session secret |
| `AWS_ACCESS_KEY_ID` | Yes | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | Yes | AWS credentials |
| `AWS_S3_BUCKET_NAME` | Yes | S3 bucket for media |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `ELEVEN_LABS_API_KEY` | Yes | ElevenLabs TTS key |
| `GOOGLE_API_KEY` | Yes | Google Maps/Places key |
| `FLASK_ENV` | No | development/production/testing |

## Next Steps (TODOs)

- [ ] Implement Sites CRUD endpoints
- [ ] Implement Media/S3 service
- [ ] Implement Maps/route optimization service
- [ ] Implement TTS service with audio caching
- [ ] Implement OpenAI service with prompts
- [ ] Add email service for password reset
- [ ] Add comprehensive tests
- [ ] Add API documentation (Swagger/OpenAPI)
- [ ] Add rate limiting
- [ ] Add request logging middleware

## Getting Help

- **Flask**: https://flask.palletsprojects.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **Flask-JWT-Extended**: https://flask-jwt-extended.readthedocs.io/
- **Alembic**: https://alembic.sqlalchemy.org/

## Notes

- This is a **clean rebuild** from the legacy server (`tours-server-legacy/`)
- Copy useful services from legacy (S3, TTS, Maps) but refactor for clarity
- The iOS app expects camelCase JSON responses (handled by `to_dict()` methods)
- Always use UTC for timestamps
