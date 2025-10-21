# Voyana Tours Server

Clean, modern Flask API server for the Voyana mobile tour application.

## Architecture

- **Framework**: Flask 3.0+ with Blueprints
- **Database**: PostgreSQL 14+ with SQLAlchemy 2.0
- **Auth**: JWT tokens (flask-jwt-extended)
- **API Design**: RESTful JSON API
- **Deployment**: Docker containers + managed PostgreSQL

## Project Structure

```
tours-server/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── models/               # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── tour.py
│   │   ├── site.py
│   │   └── feedback.py
│   ├── api/                  # API blueprints
│   │   ├── __init__.py
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── tours.py          # Tour CRUD
│   │   ├── sites.py          # Site CRUD
│   │   ├── media.py          # Image/audio/presigned URLs
│   │   └── maps.py           # Route optimization
│   ├── services/             # Business logic
│   │   ├── __init__.py
│   │   ├── s3_service.py     # AWS S3 integration
│   │   ├── tts_service.py    # ElevenLabs TTS
│   │   ├── openai_service.py # OpenAI integration
│   │   ├── maps_service.py   # Google Maps/Places
│   │   └── email_service.py  # Email sending (password reset)
│   ├── utils/                # Helper functions
│   │   ├── __init__.py
│   │   ├── decorators.py     # Auth decorators
│   │   └── validators.py     # Input validation
│   └── config/               # Configuration
│       ├── __init__.py
│       └── prompts.json      # AI prompt templates
├── migrations/               # Alembic migrations
├── tests/                    # Unit tests
├── docker-compose.yml        # Local dev setup
├── Dockerfile               # Production container
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
└── run.py                   # Application entry point
```

## Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose

### Setup

1. Copy environment template:
```bash
cp .env.example .env
# Edit .env with your API keys
```

2. Start services:
```bash
docker-compose up
```

3. Initialize database:
```bash
docker-compose exec app flask db upgrade
docker-compose exec app flask seed-dev-data
```

4. Access API:
- API: http://localhost:5000
- Health check: http://localhost:5000/api/health

## Development Workflow

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

**View logs:**
```bash
docker-compose logs -f app
```

## Production Deployment

### AWS Deployment

The application is designed to run on:
- **Compute**: AWS ECS Fargate or Elastic Beanstalk
- **Database**: AWS RDS PostgreSQL
- **Storage**: AWS S3 (already configured)

**Environment Variables (Production):**
```bash
DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/voyana
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_S3_BUCKET_NAME=voyana-tours
JWT_SECRET_KEY=xxx
OPENAI_API_KEY=xxx
ELEVEN_LABS_API_KEY=xxx
GOOGLE_API_KEY=xxx
```

### Supabase Deployment

Alternatively, deploy with Supabase PostgreSQL:
```bash
DATABASE_URL=postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres
```

## API Documentation

See [API.md](API.md) for complete endpoint documentation.

**Key Endpoints:**
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /api/tours` - List tours
- `POST /api/tours` - Create tour
- `GET /api/tours/nearby?lat=40.7&lng=-74.0` - Find nearby tours

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Yes | Secret for JWT signing |
| `AWS_ACCESS_KEY_ID` | Yes | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | Yes | AWS credentials |
| `AWS_S3_BUCKET_NAME` | Yes | S3 bucket for media |
| `AWS_S3_REGION` | No | Default: us-east-1 |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `ELEVEN_LABS_API_KEY` | Yes | ElevenLabs TTS key |
| `GOOGLE_API_KEY` | Yes | Google Maps/Places key |
| `FLASK_ENV` | No | development/production |
| `LOG_LEVEL` | No | DEBUG/INFO/WARNING/ERROR |

## Testing

```bash
# Run all tests
docker-compose exec app pytest

# Run with coverage
docker-compose exec app pytest --cov=app

# Run specific test file
docker-compose exec app pytest tests/test_auth.py
```

## Migration from Legacy Server

To import data from the old server:
```bash
docker-compose exec app python migrate_legacy_data.py
```

## Contributing

1. Create feature branch: `git checkout -b feature-name`
2. Make changes and test: `docker-compose exec app pytest`
3. Commit: `git commit -am 'Add feature'`
4. Push: `git push origin feature-name`

## License

Proprietary - Voyana
