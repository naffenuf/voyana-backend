# Rate Limiting Implementation

This document describes the comprehensive rate limiting strategy implemented across all API endpoints to prevent abuse, control costs, and ensure fair usage.

## Overview

Rate limiting is implemented using Flask-Limiter with per-user and per-IP tracking. All limits are per hour unless otherwise specified.

## Implementation Details

### Key Tracking Strategies

1. **Per-User (Authenticated)**: `key_func=lambda: f"endpoint_{get_jwt_identity()}"`
   - Tracks by user ID from JWT token
   - Used for authenticated endpoints

2. **Per-IP (Unauthenticated)**: `key_func=lambda: request.remote_addr`
   - Tracks by IP address
   - Used for auth endpoints and anonymous access

3. **Hybrid (Optional Auth)**: `key_func=lambda: get_jwt_identity() if verify_jwt_in_request(optional=True) else request.remote_addr`
   - Uses user ID if authenticated, otherwise IP
   - Used for public endpoints that support optional authentication

## Rate Limits by Category

### 🔴 CRITICAL - External API Calls (Highest Cost)

#### ElevenLabs TTS (Audio Generation)
- `POST /api/admin/upload/generate-audio` → **10/hour per user**
- `POST /api/tours/{id}/generate-audio-for-sites` → **5/hour per user** (batch operation)

#### AI Generation (OpenAI/Grok)
- `POST /api/admin/ai/generate-description` → **20/hour per user**

#### Google Places API
- `GET /api/places/search` → **100/hour per user**
- `GET /api/places/details` → **50/hour per user** (includes photo processing)
- `POST /api/places/download-photo` → **30/hour per user**

#### Google Maps API
- `POST /api/maps/route` → **100/hour per user**

### 🟠 HIGH - Resource-Intensive Operations

#### S3 Upload Operations
- `POST /api/admin/upload/image` → **50/hour per user**
- `POST /api/admin/upload/audio` → **30/hour per user**
- `POST /api/admin/tours/upload` → **100/hour per user** (bulk tour upload)

### 🟡 MEDIUM - Authentication & Security

#### Authentication Endpoints (IP-based)
- `POST /auth/register-device` → **10/hour per IP**
- `POST /auth/register` → **5/hour per IP**
- `POST /auth/login` → **20/hour per IP**
- `POST /auth/forgot-password` → **5/hour per IP**

### 🟢 LOW - Standard Operations

#### Tours CRUD
- `GET /api/tours` (list/browse) → **1000/hour per user/IP**
- `POST /api/tours` (create) → **100/hour per user**
- `GET /api/tours/{id}` → No limit (simple read)
- `PUT /api/tours/{id}` → No limit (owner/admin only)
- `DELETE /api/tours/{id}` → No limit (owner/admin only)

#### Feedback Submission
- `POST /api/feedback` → **50/hour per user/IP**

## Why These Limits?

### Cost Protection
- **External APIs are most expensive**: TTS costs per character, AI costs per token, Places/Maps cost per request
- **Lower limits on batch operations**: One call to generate-audio-for-sites can trigger multiple TTS requests
- **S3 bandwidth**: Upload limits prevent excessive bandwidth usage

### Abuse Prevention
- **Auth endpoints heavily limited**: Prevents brute force attacks and account creation spam
- **IP-based for anonymous**: Can't be bypassed by creating multiple accounts

### Fair Usage
- **Per-user tracking**: One user can't monopolize shared resources
- **Generous limits for normal usage**: 1000 tour views/hour is ~16/minute, more than enough for browsing

### iOS App Compatibility
- **High limits for read operations**: Users browsing tours won't hit limits during normal use
- **Reasonable write limits**: 100 tour creates/hour is generous for content creation
- **Hybrid tracking**: Works with both authenticated users and device tokens

## Monitoring & Adjusting Limits

### How to Check if Limits Are Being Hit

When a rate limit is exceeded, Flask-Limiter returns:
```json
{
  "error": "429 Too Many Requests: X per 1 hour"
}
```

### Adjusting Limits

Limits can be adjusted by modifying the `@limiter.limit()` decorator:

```python
@limiter.limit("NEW_LIMIT per hour", key_func=lambda: f"endpoint_{get_jwt_identity()}")
```

### Bypass for Testing

To temporarily disable rate limiting for development:

```python
# In app/__init__.py
limiter = Limiter(
    key_func=...,
    default_limits=["1000 per day", "200 per hour"],
    enabled=False  # Add this to disable
)
```

## Storage Backend

Currently using **in-memory storage** (`storage_uri="memory://"`):
- ✅ Simple, no external dependencies
- ✅ Fast
- ❌ Resets on server restart
- ❌ Doesn't work across multiple servers

### Production Recommendation

For production with multiple servers, use Redis:

```python
# In app/__init__.py
limiter = Limiter(
    key_func=lambda: ...,
    storage_uri="redis://localhost:6379"  # Update this
)
```

```bash
# In requirements.txt
redis==5.0.1
```

## Testing Rate Limits

### Manual Testing

```bash
# Test auth rate limit (5/hour)
for i in {1..6}; do
  curl -X POST http://localhost:5000/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"test'$i'@example.com","password":"pass123","name":"Test"}' \
    && echo ""
done
# 6th request should return 429
```

### Automated Testing

```python
# tests/test_rate_limiting.py
def test_auth_register_rate_limit(client):
    # Make 5 requests (should succeed)
    for i in range(5):
        response = client.post('/auth/register', json={
            'email': f'test{i}@example.com',
            'password': 'password123',
            'name': 'Test User'
        })
        assert response.status_code in [201, 400]  # 400 if email exists

    # 6th request should hit rate limit
    response = client.post('/auth/register', json={
        'email': 'test6@example.com',
        'password': 'password123',
        'name': 'Test User'
    })
    assert response.status_code == 429
```

## Endpoints WITHOUT Rate Limiting

The following endpoints currently have NO rate limiting (considered safe):

- `GET /api/tours/{id}` - Simple database read
- `GET /api/sites/{id}` - Simple database read
- `PUT /api/tours/{id}` - Already protected by ownership check
- `DELETE /api/tours/{id}` - Already protected by ownership check
- `GET /api/media/presigned-url` - Simple URL generation
- All admin read operations (`GET /api/admin/*`) - Protected by admin auth

These can be rate-limited later if needed.

## Summary

✅ **Protected**: All expensive external API calls
✅ **Protected**: All upload operations
✅ **Protected**: All authentication endpoints
✅ **Protected**: Tour/feedback creation
✅ **iOS Compatible**: High limits for browsing/viewing
✅ **Cost Controlled**: Lowest limits on most expensive operations
✅ **Abuse Resistant**: IP-based limits prevent bypass

The rate limiting strategy prioritizes protecting your costs (external APIs) while maintaining excellent user experience for normal iOS app usage.
