"""
Text-to-Speech service using Eleven Labs API with caching.
"""
import logging
import requests
import hashlib
import uuid
from flask import current_app
from app import db
from app.models.audio_cache import AudioCache
from app.services.s3_service import upload_file_to_s3

logger = logging.getLogger(__name__)

# Eleven Labs API settings
ELEVEN_LABS_API_URL = "https://api.elevenlabs.io/v1"


def generate_audio(text, voice_id=None):
    """
    Generate audio from text using Eleven Labs API with caching.

    Args:
        text: The text to convert to speech
        voice_id: The ID of the Eleven Labs voice to use (default: from config)

    Returns:
        dict: {
            'status': 'success' | 'error',
            'audio_url': S3 URL of the audio file (if success),
            'from_cache': bool (if success),
            'error': error message (if error)
        }
    """
    try:
        # Validate text
        if not text or not text.strip():
            logger.warning("Empty text provided for audio generation")
            return {
                'status': 'error',
                'error': 'Text cannot be empty'
            }

        # Use configured voice ID if not provided
        if not voice_id:
            voice_id = current_app.config.get('ELEVEN_LABS_VOICE_ID', 'XrExE9yKIg1WjnnlVkGX')

        logger.info(f"Processing TTS request - text length: {len(text)}, voice: {voice_id}")

        # Check cache first (ignore voice_id - cache by text only)
        cached_audio = AudioCache.find_by_text(text)
        if cached_audio:
            logger.info(f"Found cached audio for text hash: {cached_audio.text_hash[:8]}...")
            cached_audio.update_stats()
            db.session.commit()
            return {
                'status': 'success',
                'audio_url': cached_audio.audio_url,
                'from_cache': True
            }

        # Not cached, generate new audio
        logger.info("Audio not found in cache, generating new audio")

        # Get API key
        api_key = current_app.config.get('ELEVEN_LABS_API_KEY')
        if not api_key:
            logger.error("Eleven Labs API key not configured")
            return {
                'status': 'error',
                'error': 'TTS service not configured'
            }

        # API endpoint
        url = f"{ELEVEN_LABS_API_URL}/text-to-speech/{voice_id}"

        # Request headers
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }

        # Request body
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.75,
                "similarity_boost": 0.75
            }
        }

        # Calculate timeout based on text length (60s base + 45s per 500 chars)
        timeout = min(270, max(60, 60 + (len(text) // 500) * 45))
        logger.info(f"Making Eleven Labs API request with timeout {timeout}s")

        # Make the API request
        try:
            response = requests.post(url, json=data, headers=headers, timeout=timeout)
            response.raise_for_status()

            logger.info(f"Eleven Labs API response received: {response.status_code}")

        except requests.exceptions.Timeout:
            logger.error(f"Eleven Labs API request timed out after {timeout}s")
            return {
                'status': 'error',
                'error': 'Audio generation timed out'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Eleven Labs API request failed: {e}")
            return {
                'status': 'error',
                'error': f'Failed to generate audio: {str(e)}'
            }

        # Upload audio to S3
        audio_data = response.content
        file_name = f"tts_{uuid.uuid4()}.mp3"

        logger.info(f"Uploading audio to S3: {file_name}")
        s3_url = upload_file_to_s3(audio_data, file_name, folder='audio/tts', content_type='audio/mpeg')

        if not s3_url:
            logger.error("Failed to upload audio to S3")
            return {
                'status': 'error',
                'error': 'Failed to upload audio to storage'
            }

        # Cache the audio URL
        text_hash = AudioCache.get_hash(text)
        audio_cache = AudioCache(
            text_hash=text_hash,
            text_content=text,
            audio_url=s3_url,
            voice_id=voice_id
        )
        db.session.add(audio_cache)

        try:
            db.session.commit()
            logger.info(f"Audio generated and cached successfully: {s3_url[:80]}...")
        except Exception as commit_error:
            # Handle race condition: another request may have cached this text already
            db.session.rollback()
            logger.warning(f"Cache insert failed (likely race condition): {commit_error}")
            logger.info("Checking cache again after race condition")
            cached_audio = AudioCache.find_by_text(text)
            if cached_audio:
                logger.info("Found audio cached by concurrent request")
                return {
                    'status': 'success',
                    'audio_url': cached_audio.audio_url,
                    'from_cache': True
                }
            # If still not found, return the URL we generated anyway
            logger.warning("Cache check after race condition failed, returning generated URL")

        return {
            'status': 'success',
            'audio_url': s3_url,
            'from_cache': False
        }

    except Exception as e:
        logger.error(f"Error in generate_audio: {e}", exc_info=True)
        db.session.rollback()
        return {
            'status': 'error',
            'error': f'An unexpected error occurred: {str(e)}'
        }
