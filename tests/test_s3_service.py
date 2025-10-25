"""
Tests for S3 service functions.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from app.services.s3_service import generate_presigned_url, upload_file_to_s3


class TestGeneratePresignedUrl:
    """Tests for generate_presigned_url function."""

    def test_non_s3_url_passthrough(self, app):
        """Test that non-S3 URLs are returned unchanged."""
        with app.app_context():
            regular_url = "https://example.com/image.jpg"
            result = generate_presigned_url(regular_url)
            assert result == regular_url

    def test_empty_url(self, app):
        """Test handling of empty URL."""
        with app.app_context():
            result = generate_presigned_url("")
            assert result is None

            result = generate_presigned_url(None)
            assert result is None

    @patch('app.services.s3_service.get_s3_client')
    def test_s3_url_regional_format(self, mock_get_client, app):
        """Test presigned URL generation for regional S3 URL format."""
        with app.app_context():
            # Mock S3 client
            mock_client = Mock()
            mock_client.generate_presigned_url.return_value = 'https://presigned-url.example.com'
            mock_get_client.return_value = mock_client

            s3_url = 'https://my-bucket.s3.us-east-1.amazonaws.com/path/to/image.jpg'
            result = generate_presigned_url(s3_url)

            # Should call generate_presigned_url with correct params
            mock_client.generate_presigned_url.assert_called_once()
            call_args = mock_client.generate_presigned_url.call_args

            assert call_args[0][0] == 'get_object'
            assert call_args[1]['Params']['Key'] == 'path/to/image.jpg'
            assert result == 'https://presigned-url.example.com'

    @patch('app.services.s3_service.get_s3_client')
    def test_s3_url_global_format(self, mock_get_client, app):
        """Test presigned URL generation for global S3 URL format."""
        with app.app_context():
            mock_client = Mock()
            mock_client.generate_presigned_url.return_value = 'https://presigned.example.com'
            mock_get_client.return_value = mock_client

            s3_url = 'https://my-bucket.s3.amazonaws.com/folder/file.mp3'
            result = generate_presigned_url(s3_url)

            mock_client.generate_presigned_url.assert_called_once()
            call_args = mock_client.generate_presigned_url.call_args

            assert call_args[1]['Params']['Key'] == 'folder/file.mp3'
            assert result == 'https://presigned.example.com'

    @patch('app.services.s3_service.get_s3_client')
    def test_presigned_url_expiration(self, mock_get_client, app):
        """Test custom expiration time for presigned URL."""
        with app.app_context():
            mock_client = Mock()
            mock_client.generate_presigned_url.return_value = 'https://presigned.example.com'
            mock_get_client.return_value = mock_client

            s3_url = 'https://bucket.s3.amazonaws.com/file.jpg'
            generate_presigned_url(s3_url, expires_in=7200)

            call_args = mock_client.generate_presigned_url.call_args
            assert call_args[1]['ExpiresIn'] == 7200

    @patch('app.services.s3_service.get_s3_client')
    def test_presigned_url_cache_control(self, mock_get_client, app):
        """Test that presigned URL includes cache control headers."""
        with app.app_context():
            mock_client = Mock()
            mock_client.generate_presigned_url.return_value = 'https://presigned.example.com'
            mock_get_client.return_value = mock_client

            s3_url = 'https://bucket.s3.amazonaws.com/file.jpg'
            generate_presigned_url(s3_url)

            call_args = mock_client.generate_presigned_url.call_args
            assert call_args[1]['Params']['ResponseCacheControl'] == 'max-age=31536000, public'

    @patch('app.services.s3_service.get_s3_client')
    def test_bucket_name_extraction(self, mock_get_client, app):
        """Test extraction of bucket name from URL."""
        with app.app_context():
            mock_client = Mock()
            mock_client.generate_presigned_url.return_value = 'https://presigned.example.com'
            mock_get_client.return_value = mock_client

            s3_url = 'https://different-bucket.s3.us-west-2.amazonaws.com/file.jpg'
            generate_presigned_url(s3_url)

            call_args = mock_client.generate_presigned_url.call_args
            # Should use bucket name from URL
            assert call_args[1]['Params']['Bucket'] == 'different-bucket'

    @patch('app.services.s3_service.get_s3_client')
    def test_client_error_fallback(self, mock_get_client, app):
        """Test that ClientError causes fallback to original URL."""
        with app.app_context():
            mock_client = Mock()
            mock_client.generate_presigned_url.side_effect = ClientError(
                {'Error': {'Code': 'NoSuchKey'}},
                'generate_presigned_url'
            )
            mock_get_client.return_value = mock_client

            s3_url = 'https://bucket.s3.amazonaws.com/file.jpg'
            result = generate_presigned_url(s3_url)

            # Should return original URL on error
            assert result == s3_url


class TestUploadFileToS3:
    """Tests for upload_file_to_s3 function."""

    @patch('app.services.s3_service.get_s3_client')
    def test_upload_success(self, mock_get_client, app):
        """Test successful file upload to S3."""
        with app.app_context():
            mock_client = Mock()
            mock_client.put_object.return_value = {'ETag': 'abc123'}
            mock_get_client.return_value = mock_client

            file_data = b'test audio data'
            file_name = 'test.mp3'

            result = upload_file_to_s3(file_data, file_name)

            # Should call put_object
            mock_client.put_object.assert_called_once()
            call_args = mock_client.put_object.call_args[1]

            assert call_args['Body'] == file_data
            assert call_args['Key'] == 'audio/test.mp3'
            assert call_args['ContentType'] == 'audio/mpeg'

            # Should return S3 URL
            assert result is not None
            assert 'test.mp3' in result

    @patch('app.services.s3_service.get_s3_client')
    def test_upload_custom_folder(self, mock_get_client, app):
        """Test upload to custom folder."""
        with app.app_context():
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            upload_file_to_s3(b'data', 'file.jpg', folder='images')

            call_args = mock_client.put_object.call_args[1]
            assert call_args['Key'] == 'images/file.jpg'

    @patch('app.services.s3_service.get_s3_client')
    def test_upload_custom_content_type(self, mock_get_client, app):
        """Test upload with custom content type."""
        with app.app_context():
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            upload_file_to_s3(b'data', 'image.png', content_type='image/png')

            call_args = mock_client.put_object.call_args[1]
            assert call_args['ContentType'] == 'image/png'

    @patch('app.services.s3_service.get_s3_client')
    def test_upload_cache_control(self, mock_get_client, app):
        """Test that uploads include cache control headers."""
        with app.app_context():
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            upload_file_to_s3(b'data', 'file.mp3')

            call_args = mock_client.put_object.call_args[1]
            assert call_args['CacheControl'] == 'max-age=31536000, public'

    @patch('app.services.s3_service.get_s3_client')
    def test_upload_client_error(self, mock_get_client, app):
        """Test handling of S3 client errors."""
        with app.app_context():
            mock_client = Mock()
            mock_client.put_object.side_effect = ClientError(
                {'Error': {'Code': 'AccessDenied'}},
                'put_object'
            )
            mock_get_client.return_value = mock_client

            result = upload_file_to_s3(b'data', 'file.mp3')

            # Should return None on error
            assert result is None

    @patch('app.services.s3_service.get_s3_client')
    def test_upload_general_exception(self, mock_get_client, app):
        """Test handling of general exceptions."""
        with app.app_context():
            mock_client = Mock()
            mock_client.put_object.side_effect = Exception('Network error')
            mock_get_client.return_value = mock_client

            result = upload_file_to_s3(b'data', 'file.mp3')

            # Should return None on error
            assert result is None
