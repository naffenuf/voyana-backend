"""
Tests for TTS (Text-to-Speech) service.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from app.services.tts_service import generate_audio
from app.models.audio_cache import AudioCache
from app import db


class TestGenerateAudio:
    """Tests for generate_audio function."""

    def test_empty_text_validation(self, app):
        """Test that empty text is rejected."""
        with app.app_context():
            result = generate_audio("")
            assert result['status'] == 'error'
            assert 'empty' in result['error'].lower()

            result = generate_audio("   ")
            assert result['status'] == 'error'

    def test_cache_hit(self, app):
        """Test that cached audio is returned when available."""
        with app.app_context():
            text = "Turn left on Main Street"
            cached_url = "https://s3.amazonaws.com/bucket/cached_audio.mp3"

            # Create cache entry
            cache = AudioCache(
                text_hash=AudioCache.get_hash(text),
                text_content=text,
                audio_url=cached_url,
                voice_id='test_voice'
            )
            db.session.add(cache)
            db.session.commit()

            # Generate audio (should hit cache)
            result = generate_audio(text)

            assert result['status'] == 'success'
            assert result['audio_url'] == cached_url
            assert result['from_cache'] is True

    def test_cache_stats_update_on_hit(self, app):
        """Test that cache hit statistics are updated."""
        with app.app_context():
            text = "Turn right on Broadway"

            cache = AudioCache(
                text_hash=AudioCache.get_hash(text),
                text_content=text,
                audio_url="https://s3.amazonaws.com/bucket/audio.mp3"
            )
            db.session.add(cache)
            db.session.commit()

            initial_hit_count = cache.hit_count

            # Hit the cache
            generate_audio(text)

            # Reload from DB
            cache = AudioCache.query.get(cache.id)
            assert cache.hit_count == initial_hit_count + 1

    @patch('app.services.tts_service.upload_file_to_s3')
    @patch('app.services.tts_service.requests.post')
    def test_cache_miss_generates_audio(self, mock_post, mock_upload, app):
        """Test that audio is generated when not in cache."""
        with app.app_context():
            text = "Go straight ahead"

            # Mock successful ElevenLabs API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'fake audio data'
            mock_post.return_value = mock_response

            # Mock successful S3 upload
            s3_url = "https://s3.amazonaws.com/bucket/new_audio.mp3"
            mock_upload.return_value = s3_url

            result = generate_audio(text)

            # Should call ElevenLabs API
            mock_post.assert_called_once()

            # Should upload to S3
            mock_upload.assert_called_once()

            # Should return success with S3 URL
            assert result['status'] == 'success'
            assert result['audio_url'] == s3_url
            assert result['from_cache'] is False

    @patch('app.services.tts_service.upload_file_to_s3')
    @patch('app.services.tts_service.requests.post')
    def test_audio_cached_after_generation(self, mock_post, mock_upload, app):
        """Test that generated audio is cached."""
        with app.app_context():
            text = "Walk 100 meters"

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'audio data'
            mock_post.return_value = mock_response

            s3_url = "https://s3.amazonaws.com/bucket/audio.mp3"
            mock_upload.return_value = s3_url

            # Generate audio
            generate_audio(text)

            # Verify it was cached
            cached = AudioCache.find_by_text(text)
            assert cached is not None
            assert cached.audio_url == s3_url
            assert cached.text_content == text

    @patch('app.services.tts_service.requests.post')
    def test_elevenlabs_api_call_parameters(self, mock_post, app):
        """Test that ElevenLabs API is called with correct parameters."""
        with app.app_context():
            # Ensure text is not cached
            text = "Unique text for API test"

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'audio'
            mock_post.return_value = mock_response

            # Mock S3 upload to prevent actual upload
            with patch('app.services.tts_service.upload_file_to_s3') as mock_upload:
                mock_upload.return_value = "https://s3.amazonaws.com/audio.mp3"
                generate_audio(text, voice_id='custom_voice_123')

            # Verify API call
            call_args = mock_post.call_args

            # Check URL
            assert 'elevenlabs.io' in call_args[0][0]
            assert 'custom_voice_123' in call_args[0][0]

            # Check headers
            headers = call_args[1]['headers']
            assert headers['Content-Type'] == 'application/json'
            assert 'xi-api-key' in headers

            # Check request body
            data = call_args[1]['json']
            assert data['text'] == text
            assert data['model_id'] == 'eleven_multilingual_v2'

    @patch('app.services.tts_service.requests.post')
    def test_timeout_based_on_text_length(self, mock_post, app):
        """Test that timeout increases with text length."""
        with app.app_context():
            # Short text
            short_text = "Go"

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'audio'
            mock_post.return_value = mock_response

            with patch('app.services.tts_service.upload_file_to_s3') as mock_upload:
                mock_upload.return_value = "https://s3.amazonaws.com/audio.mp3"
                generate_audio(short_text)

            short_timeout = mock_post.call_args[1]['timeout']

            # Long text (> 500 chars)
            long_text = "a" * 1000

            with patch('app.services.tts_service.upload_file_to_s3') as mock_upload:
                mock_upload.return_value = "https://s3.amazonaws.com/audio.mp3"
                generate_audio(long_text)

            long_timeout = mock_post.call_args[1]['timeout']

            # Longer text should have longer timeout
            assert long_timeout > short_timeout

    @patch('app.services.tts_service.requests.post')
    def test_elevenlabs_api_timeout(self, mock_post, app):
        """Test handling of API timeout."""
        with app.app_context():
            text = "Test timeout"

            mock_post.side_effect = requests.exceptions.Timeout()

            result = generate_audio(text)

            assert result['status'] == 'error'
            assert 'timeout' in result['error'].lower()

    @patch('app.services.tts_service.requests.post')
    def test_elevenlabs_api_error(self, mock_post, app):
        """Test handling of API errors."""
        with app.app_context():
            text = "Test API error"

            mock_post.side_effect = requests.exceptions.RequestException("API Error")

            result = generate_audio(text)

            assert result['status'] == 'error'
            assert 'error' in result['error'].lower()

    @patch('app.services.tts_service.upload_file_to_s3')
    @patch('app.services.tts_service.requests.post')
    def test_s3_upload_failure(self, mock_post, mock_upload, app):
        """Test handling of S3 upload failure."""
        with app.app_context():
            text = "Test upload failure"

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'audio data'
            mock_post.return_value = mock_response

            # Simulate S3 upload failure
            mock_upload.return_value = None

            result = generate_audio(text)

            assert result['status'] == 'error'
            assert 'upload' in result['error'].lower()

    def test_missing_api_key(self, app):
        """Test handling of missing ElevenLabs API key."""
        with app.app_context():
            # Temporarily remove API key from config
            original_key = app.config.get('ELEVEN_LABS_API_KEY')
            app.config['ELEVEN_LABS_API_KEY'] = None

            text = "Test missing key"
            result = generate_audio(text)

            assert result['status'] == 'error'
            assert 'not configured' in result['error'].lower()

            # Restore original key
            app.config['ELEVEN_LABS_API_KEY'] = original_key

    @patch('app.services.tts_service.upload_file_to_s3')
    @patch('app.services.tts_service.requests.post')
    def test_race_condition_handling(self, mock_post, mock_upload, app):
        """Test handling of concurrent cache inserts (race condition)."""
        with app.app_context():
            text = "Race condition test"

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'audio'
            mock_post.return_value = mock_response

            s3_url = "https://s3.amazonaws.com/audio.mp3"
            mock_upload.return_value = s3_url

            # Pre-populate cache to simulate race condition
            cache = AudioCache(
                text_hash=AudioCache.get_hash(text),
                text_content=text,
                audio_url="https://s3.amazonaws.com/concurrent.mp3"
            )
            db.session.add(cache)
            db.session.commit()

            # This should hit the cache instead of trying to insert duplicate
            result = generate_audio(text)

            # Should return cached URL
            assert result['status'] == 'success'
            assert result['from_cache'] is True
