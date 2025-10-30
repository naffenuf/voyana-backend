# Voyana Tours Server - Database Schema

**Database:** PostgreSQL 14+
**ORM:** SQLAlchemy 2.0
**Migration Tool:** Alembic (via Flask-Migrate)
**Last Updated:** 2025-10-23

## Current Data
- **30 tours** (all live, public)
- **195 unique sites**
- **1 admin user** (admin@voyana.com)

---

## Table Overview

| Table | Purpose | Row Count | Key Type |
|-------|---------|-----------|----------|
| `users` | User accounts & authentication | 1 | Integer PK |
| `tours` | Tour content | 30 | UUID PK |
| `sites` | Points of interest | 195 | UUID PK |
| `tour_sites` | Tour↔Site many-to-many | 195 | Composite PK |
| `feedback` | User feedback | 0 | Integer PK |
| `api_keys` | Programmatic access | 0 | Integer PK |
| `password_reset_tokens` | Email password reset | 0 | Integer PK |
| `audio_cache` | TTS caching | 0 | UUID PK |
| `neighborhood_descriptions` | Pre-written descriptions | 0 | Integer PK |
| `alembic_version` | Migration tracking | 1 | N/A |

---

## Detailed Schema

### 1. `users` - User Accounts

User accounts with role-based permissions and OAuth support.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | `integer` | NO | Auto-increment | Primary key |
| `email` | `varchar(255)` | NO | - | Unique email address |
| `password_hash` | `varchar(256)` | YES | NULL | Hashed password (NULL for OAuth-only) |
| `name` | `varchar(255)` | YES | NULL | User's full name |
| `role` | `varchar(20)` | NO | 'creator' | User role: 'admin', 'creator', 'viewer' |
| `google_id` | `varchar(255)` | YES | NULL | Google OAuth identifier |
| `apple_id` | `varchar(255)` | YES | NULL | Apple OAuth identifier |
| `is_active` | `boolean` | NO | TRUE | Account active status |
| `email_verified` | `boolean` | NO | FALSE | Email verification status |
| `created_at` | `timestamp` | NO | `now()` | Account creation timestamp |
| `last_login_at` | `timestamp` | YES | NULL | Last login timestamp |

**Indexes:**
- `users_pkey` (PRIMARY KEY) on `id`
- `ix_users_email` (UNIQUE) on `email`
- `users_google_id_key` (UNIQUE) on `google_id`
- `users_apple_id_key` (UNIQUE) on `apple_id`

**Relationships:**
- `tours` → One-to-many (CASCADE delete)
- `api_keys` → One-to-many (CASCADE delete)
- `feedback` → One-to-many (SET NULL on delete)

**API Response Format (camelCase):**
```json
{
  "id": 1,
  "email": "admin@voyana.com",
  "name": "Voyana System",
  "role": "admin",
  "is_active": true,
  "email_verified": true,
  "created_at": "2025-10-23T17:26:01.123456",
  "last_login_at": null
}
```

---

### 2. `tours` - Tour Content

Tours containing multiple ordered sites with metadata.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | `uuid` | NO | `uuid_generate_v4()` | Primary key |
| `owner_id` | `integer` | NO | - | Foreign key → `users.id` |
| `name` | `varchar(200)` | NO | - | Tour name/title |
| `description` | `text` | YES | NULL | Full tour description |
| `city` | `varchar(100)` | YES | NULL | City name (e.g., "New York") |
| `neighborhood` | `varchar(100)` | YES | NULL | Neighborhood (e.g., "Chinatown") |
| `latitude` | `float` | YES | NULL | Tour center latitude |
| `longitude` | `float` | YES | NULL | Tour center longitude |
| `image_url` | `varchar(1024)` | YES | NULL | S3 URL for tour image |
| `audio_url` | `varchar(1024)` | YES | NULL | S3 URL for tour audio |
| `map_image_url` | `varchar(1024)` | YES | NULL | S3 URL for map image |
| `music_urls` | `varchar(1024)[]` | YES | NULL | Array of S3 URLs for background music |
| `duration_minutes` | `integer` | YES | NULL | Estimated tour duration |
| `distance_meters` | `float` | YES | NULL | Total walking distance |
| `status` | `varchar(20)` | NO | 'draft' | Tour status: 'draft', 'live', 'archived' |
| `is_public` | `boolean` | NO | FALSE | Public visibility flag |
| `created_at` | `timestamp` | NO | `now()` | Creation timestamp |
| `updated_at` | `timestamp` | NO | `now()` | Last update timestamp |
| `published_at` | `timestamp` | YES | NULL | Publication timestamp |

**Indexes:**
- `tours_pkey` (PRIMARY KEY) on `id`

**Foreign Keys:**
- `owner_id` → `users.id` (CASCADE delete)

**Relationships:**
- `owner` → Many-to-one to `users`
- `tour_sites` → One-to-many (CASCADE delete)
- `feedback` → One-to-many (CASCADE delete)

**API Response Format (camelCase):**
```json
{
  "id": "203b61a2-34a0-436e-bc87-c15c94de2f3a",
  "name": "Chinatown Cultural Heart Tour",
  "description": "Embark on the 'Chinatown Cultural Heart Tour'...",
  "city": "New York",
  "neighborhood": "Chinatown",
  "latitude": 40.7143521,
  "longitude": -73.9979432,
  "imageUrl": "https://...",
  "audioUrl": null,
  "mapImageUrl": "https://...",
  "musicUrls": null,
  "durationMinutes": 90,
  "distanceMeters": 909.0,
  "status": "live",
  "isPublic": true,
  "createdAt": "2025-10-23T17:26:01.308314",
  "updatedAt": "2025-10-23T17:26:01.308314",
  "publishedAt": null,
  "siteIds": ["7ba66e24-...", "3d774efb-..."],
  "sites": [...]
}
```

---

### 3. `sites` - Points of Interest

Individual locations/attractions that can be part of multiple tours.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | `uuid` | NO | `uuid_generate_v4()` | Primary key |
| `title` | `varchar(200)` | NO | - | Site name |
| `description` | `text` | YES | NULL | Full site description |
| `latitude` | `float` | NO | - | Site latitude (required) |
| `longitude` | `float` | NO | - | Site longitude (required) |
| `user_submitted_locations` | `float[]` | YES | NULL | 2D array of user-submitted viewing locations [[lat, lng], ...] |
| `image_url` | `varchar(1024)` | YES | NULL | S3 URL for site image |
| `audio_url` | `varchar(1024)` | YES | NULL | S3 URL for site audio |
| `web_url` | `varchar(1024)` | YES | NULL | External website URL |
| `keywords` | `varchar(50)[]` | YES | NULL | Array of keywords/tags |
| `rating` | `float` | YES | NULL | Site rating (0-5) |
| `city` | `varchar(100)` | YES | NULL | City name |
| `neighborhood` | `varchar(100)` | YES | NULL | Neighborhood name |
| `place_id` | `varchar(255)` | YES | NULL | Google Places ID |
| `formatted_address` | `text` | YES | NULL | Google Places formatted address |
| `types` | `varchar(50)[]` | YES | NULL | Google Places types |
| `user_ratings_total` | `integer` | YES | NULL | Google Places review count |
| `phone_number` | `text` | YES | NULL | Google Places phone number |
| `google_photo_references` | `varchar(1024)[]` | YES | NULL | Array of Google photo URLs |
| `created_at` | `timestamp` | NO | `now()` | Creation timestamp |
| `updated_at` | `timestamp` | NO | `now()` | Last update timestamp |

**Indexes:**
- `sites_pkey` (PRIMARY KEY) on `id`
- `ix_sites_place_id` on `place_id`

**Relationships:**
- `tour_sites` → One-to-many (CASCADE delete)
- `feedback` → One-to-many (CASCADE delete)

**API Response Format (camelCase):**
```json
{
  "id": "7ba66e24-5613-4a92-9b48-2f366a5cbceb",
  "title": "Doyers Street",
  "description": "Winding through the heart of Chinatown...",
  "latitude": 40.7143521,
  "longitude": -73.9979432,
  "imageUrl": "https://...",
  "audioUrl": null,
  "webUrl": null,
  "keywords": ["route"],
  "rating": 4.4,
  "city": "New York",
  "neighborhood": "Chinatown",
  "placeId": "ChIJ27bN9yZawokRc9Z6LnID29s",
  "formattedAddress": "Doyers St, New York, NY, USA",
  "types": ["route"],
  "userRatingsTotal": 175,
  "phoneNumber": null,
  "googlePhotoReferences": [],
  "createdAt": "2025-10-23T17:26:01.309891",
  "updatedAt": "2025-10-23T17:26:01.309893"
}
```

---

### 4. `tour_sites` - Tour↔Site Junction Table

Many-to-many relationship between tours and sites with ordering.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `tour_id` | `uuid` | NO | - | Foreign key → `tours.id` (composite PK) |
| `site_id` | `uuid` | NO | - | Foreign key → `sites.id` (composite PK) |
| `display_order` | `integer` | NO | - | Site ordering in tour (1, 2, 3...) |
| `visit_duration_minutes` | `integer` | YES | NULL | Recommended visit duration |

**Indexes:**
- `tour_sites_pkey` (PRIMARY KEY) on `(tour_id, site_id)`

**Foreign Keys:**
- `tour_id` → `tours.id` (CASCADE delete)
- `site_id` → `sites.id` (CASCADE delete)

**Relationships:**
- `tour` → Many-to-one to `tours`
- `site` → Many-to-one to `sites`

---

### 5. `feedback` - User Feedback

User-submitted feedback for tours or sites.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | `integer` | NO | Auto-increment | Primary key |
| `tour_id` | `uuid` | YES | NULL | Foreign key → `tours.id` |
| `site_id` | `uuid` | YES | NULL | Foreign key → `sites.id` |
| `user_id` | `integer` | YES | NULL | Foreign key → `users.id` |
| `feedback_type` | `varchar(50)` | NO | - | Type: 'issue', 'suggestion', 'rating', 'comment', 'photo' |
| `rating` | `integer` | YES | NULL | Numerical rating (1-5) |
| `comment` | `text` | YES | NULL | User comment text |
| `photo_data` | `text` | YES | NULL | Base64-encoded photo (for 'photo' type only) |
| `status` | `varchar(20)` | NO | 'pending' | Status: 'pending', 'reviewed', 'resolved' |
| `admin_notes` | `text` | YES | NULL | Admin notes (internal) |
| `created_at` | `timestamp` | NO | `now()` | Submission timestamp |
| `reviewed_at` | `timestamp` | YES | NULL | Review timestamp |
| `reviewed_by` | `integer` | YES | NULL | Foreign key → `users.id` (reviewer) |

**Indexes:**
- `feedback_pkey` (PRIMARY KEY) on `id`

**Foreign Keys:**
- `tour_id` → `tours.id` (CASCADE delete)
- `site_id` → `sites.id` (CASCADE delete)
- `user_id` → `users.id` (SET NULL on delete)
- `reviewed_by` → `users.id` (SET NULL on delete)

**Constraints:**
- Either `tour_id` OR `site_id` must be set (not both)
- Photo feedback (`feedback_type='photo'`) should only be used for sites (not tours)

**Photo Feedback Use Case:**
The 'photo' feedback type enables users to submit better photos for sites than the ones currently displayed. When users visit a site and find the existing photo inadequate, they can:
1. Take a photo on their device
2. Client resizes/optimizes the photo before submission
3. Submit as base64-encoded data in `photo_data` field
4. Admin reviews in admin dashboard
5. Admin can replace the site's main photo if the submitted photo is better quality

This crowdsourced approach improves site photo quality over time.

---

### 6. `api_keys` - Programmatic API Access

API keys for external integrations and programmatic access.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | `integer` | NO | Auto-increment | Primary key |
| `key` | `varchar(64)` | NO | - | URL-safe API key (unique) |
| `name` | `varchar(64)` | NO | - | Human-readable key name |
| `user_id` | `integer` | YES | NULL | Foreign key → `users.id` |
| `created_at` | `timestamp` | NO | `now()` | Creation timestamp |
| `last_used_at` | `timestamp` | YES | NULL | Last usage timestamp |
| `is_active` | `boolean` | NO | TRUE | Active status flag |

**Indexes:**
- `api_keys_pkey` (PRIMARY KEY) on `id`
- `ix_api_keys_key` (UNIQUE) on `key`

**Foreign Keys:**
- `user_id` → `users.id` (CASCADE delete)

---

### 7. `password_reset_tokens` - Email Password Reset

Temporary tokens for email-based password reset flow.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | `integer` | NO | Auto-increment | Primary key |
| `user_id` | `integer` | NO | - | Foreign key → `users.id` |
| `token` | `varchar(64)` | NO | - | URL-safe reset token (unique) |
| `expires_at` | `timestamp` | NO | - | Token expiration time (24h default) |
| `used` | `boolean` | NO | FALSE | Token used status |
| `created_at` | `timestamp` | NO | `now()` | Creation timestamp |

**Indexes:**
- `password_reset_tokens_pkey` (PRIMARY KEY) on `id`
- `ix_password_reset_tokens_token` (UNIQUE) on `token`

**Foreign Keys:**
- `user_id` → `users.id` (CASCADE delete)

---

### 8. `audio_cache` - TTS Audio Caching

Cache for text-to-speech generated audio files to avoid duplicate generation.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | `uuid` | NO | `uuid_generate_v4()` | Primary key |
| `text_hash` | `varchar(64)` | NO | - | MD5 hash of text content (unique) |
| `text_content` | `text` | NO | - | Original text |
| `audio_url` | `varchar(1024)` | NO | - | S3 URL of generated audio |
| `voice_id` | `varchar(64)` | NO | - | TTS voice identifier |
| `created_at` | `timestamp` | NO | `now()` | Creation timestamp |
| `last_accessed_at` | `timestamp` | NO | `now()` | Last access timestamp |
| `access_count` | `integer` | YES | 0 | Access count for analytics |

**Indexes:**
- `audio_cache_pkey` (PRIMARY KEY) on `id`
- `ix_audio_cache_text_hash` (UNIQUE) on `text_hash`

---

### 9. `neighborhood_descriptions` - Pre-written Descriptions

Pre-written descriptions for neighborhoods to avoid repeated AI generation.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | `integer` | NO | Auto-increment | Primary key |
| `city` | `varchar(100)` | NO | - | City name |
| `neighborhood` | `varchar(100)` | NO | - | Neighborhood name |
| `description` | `text` | NO | - | Pre-written description |
| `created_at` | `timestamp` | NO | `now()` | Creation timestamp |
| `updated_at` | `timestamp` | NO | `now()` | Last update timestamp |

**Indexes:**
- `neighborhood_descriptions_pkey` (PRIMARY KEY) on `id`
- `unique_city_neighborhood` (UNIQUE) on `(city, neighborhood)`

---

## Entity Relationship Diagram

```
┌─────────────┐
│   users     │
│  (id: int)  │
└──────┬──────┘
       │ 1
       │
       │ *
┌──────▼──────────┐
│     tours       │
│   (id: uuid)    │◄────┐
└──────┬──────────┘     │
       │ 1               │ *
       │                 │
       │ *        ┌──────┴──────┐
       ├──────────►  tour_sites │
       │           │  (junction) │
       │           └──────┬──────┘
       │                  │ *
       │                  │
       │ 1         ┌──────▼──────┐
       │           │    sites    │
       │           │  (id: uuid) │
       │           └──────┬──────┘
       │                  │
       │                  │ 1
       │                  │
       │ *         ┌──────▼──────┐
       └───────────►  feedback   │
                   │  (id: int)  │
                   └─────────────┘

┌─────────────┐       ┌──────────────────────────┐
│  api_keys   │       │ password_reset_tokens    │
│  (id: int)  │       │       (id: int)          │
└──────┬──────┘       └──────────┬───────────────┘
       │                          │
       │ *                        │ *
       └────────┐        ┌────────┘
                │        │
                │ 1      │ 1
           ┌────▼────────▼─────┐
           │      users         │
           │    (id: int)       │
           └────────────────────┘

┌──────────────────┐       ┌───────────────────────────┐
│   audio_cache    │       │ neighborhood_descriptions │
│   (id: uuid)     │       │        (id: int)          │
└──────────────────┘       └───────────────────────────┘
  (standalone)                    (standalone)
```

---

## Common Query Examples

### Get All Live Public Tours with Sites
```sql
SELECT t.*,
       json_agg(json_build_object(
         'id', s.id,
         'title', s.title,
         'latitude', s.latitude,
         'longitude', s.longitude,
         'display_order', ts.display_order
       ) ORDER BY ts.display_order) as sites
FROM tours t
LEFT JOIN tour_sites ts ON t.id = ts.tour_id
LEFT JOIN sites s ON ts.site_id = s.id
WHERE t.status = 'live' AND t.is_public = true
GROUP BY t.id
ORDER BY t.created_at DESC;
```

### Get Tours by City and Neighborhood
```sql
SELECT * FROM tours
WHERE city = 'New York'
  AND neighborhood = 'Chinatown'
  AND status = 'live'
  AND is_public = true;
```

### Get Site with All Associated Tours
```sql
SELECT s.*,
       json_agg(json_build_object(
         'tour_id', t.id,
         'tour_name', t.name,
         'display_order', ts.display_order
       )) as tours
FROM sites s
LEFT JOIN tour_sites ts ON s.id = ts.site_id
LEFT JOIN tours t ON ts.tour_id = t.id
WHERE s.id = '7ba66e24-5613-4a92-9b48-2f366a5cbceb'
GROUP BY s.id;
```

### Add Site to Tour
```sql
INSERT INTO tour_sites (tour_id, site_id, display_order)
VALUES (
  '203b61a2-34a0-436e-bc87-c15c94de2f3a',
  '7ba66e24-5613-4a92-9b48-2f366a5cbceb',
  (SELECT COALESCE(MAX(display_order), 0) + 1
   FROM tour_sites
   WHERE tour_id = '203b61a2-34a0-436e-bc87-c15c94de2f3a')
);
```

### Check Audio Cache Before Generating
```sql
SELECT audio_url FROM audio_cache
WHERE text_hash = md5('Your text content here');
```

### Get Pending Feedback Count by Tour
```sql
SELECT t.name, COUNT(f.id) as pending_count
FROM tours t
LEFT JOIN feedback f ON t.id = f.tour_id
WHERE f.status = 'pending'
GROUP BY t.id, t.name
ORDER BY pending_count DESC;
```

---

## Migration History

| Version | Date | Description |
|---------|------|-------------|
| `a5f1dc324b18` | 2025-10-23 | Initial schema with users, tours, sites, and relationships |
| `6ca4acaf6756` | 2025-10-23 | Add city and neighborhood fields to sites table |

---

## Notes

### UUID vs Integer Primary Keys
- **Tours & Sites:** Use UUID for public-facing IDs (harder to enumerate, better for APIs)
- **Users & Feedback:** Use integer for internal relationships (better performance, simpler joins)

### CASCADE Delete Behavior
- User deleted → All their tours, API keys, and tokens deleted
- Tour deleted → All tour_sites relationships deleted (sites remain)
- Site deleted → All tour_sites relationships deleted (tours remain)
- Feedback preserved even if user deleted (user_id set to NULL)

### Array Columns
PostgreSQL arrays used for:
- `music_urls` - Multiple background music tracks
- `keywords` - Site tags/categories
- `types` - Google Places types
- `google_photo_references` - Multiple photo URLs
- `user_submitted_locations` - 2D array of coordinates

### Owner ID Constraint
- Tours require an `owner_id` (not nullable)
- Seed tours owned by admin user (id: 1)
- Prevents orphaned tours

### Timestamp Behavior
- `created_at` - Set once at creation, never changes
- `updated_at` - Automatically updated on every modification
- `published_at` - Manually set when status changes to 'live'
