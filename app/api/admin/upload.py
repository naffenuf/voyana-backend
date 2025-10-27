"""
Admin file upload endpoints.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from app.services.s3_service import upload_file_to_s3
from app.services.tts_service import generate_audio
from app.utils.admin_required import admin_required
import uuid
import os

admin_upload_bp = Blueprint('admin_upload', __name__)

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'm4a', 'aac', 'ogg'}

# Max file sizes (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50 MB


def allowed_file(filename, allowed_extensions):
    """Check if a filename has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_content_type(filename):
    """Get the MIME content type based on file extension."""
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    content_types = {
        # Images
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
        # Audio
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'm4a': 'audio/mp4',
        'aac': 'audio/aac',
        'ogg': 'audio/ogg',
    }

    return content_types.get(extension, 'application/octet-stream')


@admin_upload_bp.route('/image', methods=['POST'])
@jwt_required()
@admin_required()
def upload_image():
    """
    Upload an image file to S3 (admin only).

    Request:
        Content-Type: multipart/form-data
        Body:
            - file: Image file
            - folder: Optional folder/prefix (default: 'images')

    Returns:
        {
            "url": "https://...",
            "filename": "original-filename.jpg"
        }
    """
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    # Check if filename is empty
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Validate file extension
    if not allowed_file(file.filename, ALLOWED_IMAGE_EXTENSIONS):
        return jsonify({
            'error': f'Invalid file type. Allowed types: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}'
        }), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_IMAGE_SIZE:
        return jsonify({
            'error': f'File too large. Maximum size: {MAX_IMAGE_SIZE // (1024 * 1024)} MB'
        }), 400

    # Generate unique filename
    original_filename = secure_filename(file.filename)
    extension = original_filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4()}.{extension}"

    # Get folder from form data or use default
    folder = request.form.get('folder', 'images')

    # Get content type
    content_type = get_content_type(original_filename)

    # Upload to S3
    file_url = upload_file_to_s3(
        file_data=file.read(),
        file_name=unique_filename,
        folder=folder,
        content_type=content_type
    )

    if not file_url:
        return jsonify({'error': 'Failed to upload file to S3'}), 500

    current_app.logger.info(f'Image uploaded: {file_url}')

    return jsonify({
        'url': file_url,
        'filename': original_filename
    }), 201


@admin_upload_bp.route('/audio', methods=['POST'])
@jwt_required()
@admin_required()
def upload_audio():
    """
    Upload an audio file to S3 (admin only).

    Request:
        Content-Type: multipart/form-data
        Body:
            - file: Audio file
            - folder: Optional folder/prefix (default: 'audio')

    Returns:
        {
            "url": "https://...",
            "filename": "original-filename.mp3"
        }
    """
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    # Check if filename is empty
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Validate file extension
    if not allowed_file(file.filename, ALLOWED_AUDIO_EXTENSIONS):
        return jsonify({
            'error': f'Invalid file type. Allowed types: {", ".join(ALLOWED_AUDIO_EXTENSIONS)}'
        }), 400

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_AUDIO_SIZE:
        return jsonify({
            'error': f'File too large. Maximum size: {MAX_AUDIO_SIZE // (1024 * 1024)} MB'
        }), 400

    # Generate unique filename
    original_filename = secure_filename(file.filename)
    extension = original_filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4()}.{extension}"

    # Get folder from form data or use default
    folder = request.form.get('folder', 'audio')

    # Get content type
    content_type = get_content_type(original_filename)

    # Upload to S3
    file_url = upload_file_to_s3(
        file_data=file.read(),
        file_name=unique_filename,
        folder=folder,
        content_type=content_type
    )

    if not file_url:
        return jsonify({'error': 'Failed to upload file to S3'}), 500

    current_app.logger.info(f'Audio uploaded: {file_url}')

    return jsonify({
        'url': file_url,
        'filename': original_filename
    }), 201


@admin_upload_bp.route('/generate-audio', methods=['POST'])
@jwt_required()
@admin_required()
def generate_tts_audio():
    """
    Generate audio from text using TTS and upload to S3 (admin only).

    Request:
        Content-Type: application/json
        Body:
            {
                "text": "Text to convert to speech",
                "voice_id": "optional-voice-id"
            }

    Returns:
        {
            "url": "https://...",
            "from_cache": true/false
        }
    """
    try:
        data = request.get_json()

        if not data or 'text' not in data:
            return jsonify({'error': 'Text is required'}), 400

        text = data.get('text', '').strip()
        voice_id = data.get('voice_id')

        if not text:
            return jsonify({'error': 'Text cannot be empty'}), 400

        current_app.logger.info(f'Generating audio for text (length: {len(text)})')

        # Generate audio using TTS service
        result = generate_audio(text, voice_id=voice_id)

        if result['status'] == 'error':
            current_app.logger.error(f'TTS generation failed: {result.get("error")}')
            return jsonify({'error': result.get('error', 'Failed to generate audio')}), 500

        current_app.logger.info(f'Audio generated successfully (from_cache: {result.get("from_cache", False)})')

        return jsonify({
            'url': result['audio_url'],
            'from_cache': result.get('from_cache', False)
        }), 201

    except Exception as e:
        current_app.logger.error(f'Error in generate_tts_audio: {e}', exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500
