# AskLandmark PRD (v2.0)

**App Name:** AskLandmark
**Type:** Standalone SwiftUI iOS app (v1) + backend endpoints on existing Voyana tours-server.
**Target:** iOS 18+, SwiftUI, iPhone-focused for walking use.

## Vision

A minimal, delightful tool where users photograph a landmark and instantly hear an engaging spoken narration about it, then ask follow-up questions conversationally. It should feel like ChatGPT Voice for landmarks — not a request/response API, but a fluid, streaming interaction.

## Problem / Opportunity

Users at landmarks want instant, context-aware explanations and Q&A without reading screens or relying on guides. Existing apps are either pre-recorded (inflexible) or slow. AskLandmark delivers fast, grounded, multimodal AI narration optimized for walking.

**Business Goals:**
- Validate AI narration for Voyana integration
- Build a shared landmark database (sites table) that enriches the Voyana Tours ecosystem
- Low-cost prototype; collect usage data on real-time AI narration

**Success Metrics:**
- First audio <3s cached, <5s new landmark (90th percentile)
- 60%+ of sessions include at least one follow-up question
- Crash-free sessions >99%
- Site cache hit rate >40% after 90 days

## Architecture Decisions (Locked Down)

These decisions have been made and should not be revisited during implementation:

### 1. OpenAI Realtime API (gpt-realtime-2) as Primary Provider

The `gpt-realtime-2` model accepts image input and streams simultaneous text + audio output over a single WebSocket. This means one connection produces the landmark identification, narration text, and spoken audio together. Follow-up Q&A continues on the same session with full context.

This was chosen over:
- **Grok vision + Grok TTS** — cheaper (~$0.013 vs ~$0.15/session) but requires orchestrating separate text and TTS calls. Consider as a v2 cost optimization.
- **ElevenLabs TTS** — our existing `tts_service.py` is batch/synchronous (waits for full text, generates full MP3, uploads to S3). Not suitable for real-time streaming.

### 2. Server-Proxied Streaming

All AI API keys live on the Voyana backend. The iOS app never holds API secrets. The backend opens the Realtime WebSocket to OpenAI and proxies text + audio chunks down to the iOS client via SSE.

Benefits beyond security: per-device rate limiting, cost control, AITrace logging, provider swappability without app updates.

### 3. Cache-First via place_id

Every identification checks the `sites` table before invoking the Realtime API. The Google Places `place_id` (already an indexed field on our Site model) is the dedup key.

**Two response paths:**
- **Cached site exists:** Return the site's description text + S3 audio URL as a normal JSON response. Near-instant, near-free (only the initial vision identification call costs anything).
- **New landmark:** Stream narration via the Realtime API. On completion, persist a new Site record with the description, upload the audio to S3, and hydrate with Google Places data. Next user who photographs the same landmark gets the cached path.

### 4. Shared Sites Table

AskLandmark writes to the same `sites` table used by Voyana Tours. Sites created by AskLandmark should be distinguishable (e.g., null owner, or a source flag) but are first-class Site records that can later be adopted into curated Voyana Tours.

### 5. Anonymous Device Auth

No user accounts for v1. Issue a JWT on first launch tied to a device identifier. Use this for rate limiting, usage tracking, and session management. Follow the existing JWT patterns in the codebase (`flask_jwt_extended`).

### 6. Reuse Existing Infrastructure

The implementing agent should leverage:
- **Site model** (`app/models/site.py`) — place_id, description, audio_url, Google Places fields
- **AI service** (`app/services/ai_service.py`) — for the vision identification call; extend for Realtime WebSocket
- **S3 service** (`app/services/s3_service.py`) — for storing generated audio after streaming completes
- **AITrace model** (`app/models/ai_trace.py`) — log all AI calls
- **Google Places integration** (`app/api/places.py`) — for place_id lookup and data hydration
- **Rate limiter** — existing `@limiter.limit()` decorator
- **Blueprint registration pattern** — `app/__init__.py:register_blueprints()`
- **Prompts system** — `app/config/prompts.json` for prompt configuration

## User Experience

### Core Flow

1. **Capture:** User opens app → full-screen camera → takes photo (or picks from library). Device location is captured automatically.

2. **Identify:** Photo + coords go to the backend. The landmark name appears on screen within ~1-2 seconds. If this is a known landmark, the full narration and audio are available immediately.

3. **Narrate:** For new landmarks, text and audio stream simultaneously. The user sees text appearing and hears the narration starting within a few seconds. For cached landmarks, text displays and audio plays from the stored URL. Narration should be factual, engaging, 45-90 seconds, in a warm tour-guide voice.

4. **Ask:** An always-visible "Ask AI" button lets users ask follow-up questions by voice or text. Responses stream back as text + audio in the same tour-guide character, grounded to the landmark context. Conversation history (up to ~5-8 turns) is maintained.

5. **New Place:** User taps to start fresh — clears the session, returns to camera.

### Audio Player

Standard playback controls: play/pause, replay, speed adjustment. Controls must be large and usable one-handed while walking outdoors. Audio should auto-play and handle backgrounding gracefully.

### Session History

Persist the last ~5 sessions locally so users can revisit recent landmarks (text + audio). Each session is tied to a site_id.

### Settings

Voice selection, narration length preference (short/medium/detailed), cache management. Stored in UserDefaults.

## Constraints

- **On-device preprocessing:** Resize images to ≤1536px longest side, JPEG ~75% quality before sending to backend.
- **Rate limits:** ~20 new identifications/day per device, ~50 follow-ups/day. Cached lookups can be more generous.
- **Image size:** ≤2MB after compression.
- **Concurrency:** Flask synchronous workers hold a connection for the duration of each SSE stream. Acceptable for v1 traffic; may need gevent/async workers at scale.
- **Voice input:** Prefer on-device speech-to-text (Apple SpeechAnalyzer/SpeechTranscriber) so audio doesn't leave the device unnecessarily.
- **Offline:** Cached sessions should be viewable offline (stored text + downloaded audio).

## Non-Functional Requirements

- Minimalist, high-contrast UI; large tap targets; VoiceOver accessible; sunlight-readable.
- Graceful error handling: network failures, low confidence identifications, rate limit exceeded.
- iOS 18+, SwiftUI, MVVM or similar architecture.

## Out of Scope (v1)

- Multi-language narration
- AR overlays
- Full map integration
- User accounts / social features
- Advanced analytics dashboard
- Offline AI generation
- Direct Voyana Tours integration (v2)

## Future Considerations (v2+)

- **Grok as cost-optimized provider** — lower per-session cost, swap behind the same backend interface.
- **Voyana Tours integration** — AskLandmark sites adopted into curated tours via the shared sites table.
- **Voice Agent mode** — fully hands-free interaction using OpenAI Realtime voice-in/voice-out.
- **Popular landmark pre-caching** — analytics on most-photographed landmarks, pre-generate and cache.
- **Multi-language** — Realtime API supports multilingual output.
