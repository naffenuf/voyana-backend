"""
Google Places API endpoints for site discovery and creation.
"""
import logging
import requests
import io
import hashlib
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app.services.s3_service import upload_file_to_s3

logger = logging.getLogger(__name__)

places_bp = Blueprint('places', __name__, url_prefix='/api/places')

# Places API (New) v1 endpoints
PLACES_API_BASE_URL = "https://places.googleapis.com/v1"
TEXT_SEARCH_ENDPOINT = f"{PLACES_API_BASE_URL}/places:searchText"
PLACE_DETAILS_ENDPOINT = f"{PLACES_API_BASE_URL}/places"


def _download_and_upload_photo_to_s3(photo_name: str, place_id: str, api_key: str) -> str:
    """
    Helper function to download a photo from Google Places and upload to S3.

    Args:
        photo_name: Google Places photo resource name (e.g., "places/{place_id}/photos/{photo_id}")
        place_id: Google Places place_id (for filename generation)
        api_key: Google API key

    Returns:
        S3 URL of the uploaded photo, or None if failed
    """
    if not photo_name or '/' not in photo_name:
        logger.error(f"Invalid photo name: {photo_name}")
        return None

    try:
        # Download photo from Google
        photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?key={api_key}&maxWidthPx=800"
        logger.info(f"Fetching photo: {photo_url}")

        response = requests.get(photo_url, timeout=10)
        if response.status_code != 200:
            logger.error(f"Photo request failed: status={response.status_code}, body={response.text}")
            return None

        photo_data = response.content
        logger.info(f"Photo fetched successfully, size: {len(photo_data)} bytes")

        # Generate shortened filename using MD5 hash
        photo_id = photo_name.split('/')[-1]
        short_photo_id = hashlib.md5(photo_id.encode()).hexdigest()
        filename = f"{place_id}_{short_photo_id}.jpg"

        # Get content type
        content_type = response.headers.get('Content-Type', 'image/jpeg')

        # Create file-like object
        image_file = io.BytesIO(photo_data)
        image_file.seek(0)

        # Upload to S3
        logger.info(f"Uploading to S3: {filename}")

        from app.services.s3_service import get_s3_client
        s3_client = get_s3_client()
        bucket_name = current_app.config['AWS_S3_BUCKET_NAME']
        region = current_app.config['AWS_S3_REGION']
        object_key = f"sites/{filename}"

        # Upload file (private)
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=image_file,
            ContentType=content_type,
            CacheControl='max-age=31536000, public'
        )

        # Return raw S3 URL
        raw_s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{object_key}"
        logger.info(f"Photo uploaded to S3: {raw_s3_url}")

        # Generate presigned URL for display (valid for 7 days)
        from app.services.s3_service import generate_presigned_url
        presigned_url = generate_presigned_url(raw_s3_url, expires_in=604800)

        logger.info(f"Generated presigned URL for photo display")
        return {'url': raw_s3_url, 'presignedUrl': presigned_url}

    except requests.RequestException as e:
        logger.error(f"Failed to fetch photo: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Failed to upload photo to S3: {str(e)}")
        return None


@places_bp.route('/search', methods=['GET'])
@jwt_required()
def search_places():
    """
    Search for places using Google Places API (New) v1 Text Search.

    Query params:
        query (str): Search query (e.g., "Statue of Liberty")
        latitude (float): Latitude for location bias
        longitude (float): Longitude for location bias
        radius (int): Search radius in meters (default: 5000)

    Returns:
        JSON with array of place results
    """
    try:
        query = request.args.get('query')
        latitude = request.args.get('latitude', type=float)
        longitude = request.args.get('longitude', type=float)

        if not query:
            return jsonify({'error': 'Query parameter is required'}), 400

        if not latitude or not longitude:
            return jsonify({'error': 'Latitude and longitude parameters are required'}), 400

        api_key = current_app.config.get('GOOGLE_API_KEY')
        if not api_key:
            return jsonify({'error': 'Google API key not configured'}), 500

        logger.info(f"Searching places: query='{query}', location=({latitude},{longitude})")

        # Use Places API (New) v1 Text Search
        payload = {
            "textQuery": query.strip(),
            "maxResultCount": 10,
            "languageCode": "en",
            "locationBias": {
                "rectangle": {
                    "low": {"latitude": latitude - 0.01, "longitude": longitude - 0.01},
                    "high": {"latitude": latitude + 0.01, "longitude": longitude + 0.01}
                }
            }
        }

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.id,places.formattedAddress,places.location,places.types,places.rating,places.userRatingCount"
        }

        response = requests.post(TEXT_SEARCH_ENDPOINT, json=payload, headers=headers)

        if response.status_code != 200:
            logger.error(f"Places API error: {response.status_code} - {response.text}")
            return jsonify({
                'error': f'Places API error: {response.status_code}',
                'details': response.text
            }), response.status_code

        results = response.json()
        places_data = results.get("places", [])

        # Format results for frontend
        places = []
        for place in places_data:
            place_data = {
                'placeId': place.get('id', ''),
                'name': place.get('displayName', {}).get('text', ''),
                'formattedAddress': place.get('formattedAddress', ''),
                'location': {
                    'latitude': place.get('location', {}).get('latitude'),
                    'longitude': place.get('location', {}).get('longitude')
                },
                'types': place.get('types', []),
                'rating': place.get('rating'),
                'userRatingsTotal': place.get('userRatingCount'),
            }
            places.append(place_data)

        logger.info(f"Found {len(places)} places")
        return jsonify({
            'results': places,
            'status': 'OK'
        }), 200

    except Exception as e:
        logger.error(f"Error searching places: {e}", exc_info=True)
        return jsonify({'error': f'Error searching places: {str(e)}'}), 500


@places_bp.route('/details', methods=['GET'])
@jwt_required()
def get_place_details():
    """
    Get detailed information about a specific place using Places API (New) v1.

    Query params:
        place_id (str): Google Places place_id

    Returns:
        JSON with detailed place information including photos
    """
    try:
        place_id = request.args.get('place_id')

        if not place_id:
            return jsonify({'error': 'place_id parameter is required'}), 400

        api_key = current_app.config.get('GOOGLE_API_KEY')
        if not api_key:
            return jsonify({'error': 'Google API key not configured'}), 500

        logger.info(f"Fetching place details: place_id={place_id}")

        # Use Places API (New) v1
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": (
                "displayName,id,location,types,formattedAddress,rating,userRatingCount,"
                "websiteUri,internationalPhoneNumber,photos,editorialSummary"
            )
        }

        endpoint = f"{PLACE_DETAILS_ENDPOINT}/{place_id}"
        response = requests.get(endpoint, headers=headers)

        if response.status_code != 200:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
            logger.error(f"Place details error: {error_msg}")
            return jsonify({'error': f"Failed to get place details: {error_msg}"}), response.status_code

        place = response.json()

        # Download all photos to S3 (two-step process like legacy server)
        photos = []
        curated_image_urls = []
        user_image_urls = []
        photo_attributions = []

        for photo in place.get('photos', [])[:10]:  # Limit to 10 photos
            photo_name = photo.get('name', '')
            if not photo_name:
                logger.warning(f"Skipping photo with no name for place {place_id}")
                continue

            # Download photo from Google and upload to S3
            photo_result = _download_and_upload_photo_to_s3(photo_name, place_id, api_key)
            if not photo_result:
                logger.warning(f"Failed to process photo {photo_name} for place {place_id}")
                continue

            raw_url = photo_result['url']
            presigned_url = photo_result['presignedUrl']

            # Check if this is a user photo or curated photo
            attributions = []
            is_user_photo = False
            for attr in photo.get('authorAttributions', []):
                if attr.get('displayName'):
                    attributions.append(attr.get('displayName'))
                    if "Google" not in attr.get('displayName', ''):
                        is_user_photo = True

            photo_attributions.append(attributions)

            # Store photo with both URLs
            photo_data = {
                'photoReference': photo_name,  # Keep original photo name for reference
                'url': raw_url,  # Raw S3 URL for saving to database
                'presignedUrl': presigned_url,  # Presigned URL for display
                'width': photo.get('widthPx', 0),
                'height': photo.get('heightPx', 0),
                'htmlAttributions': attributions
            }
            photos.append(photo_data)

            # Categorize photos (use raw URL)
            if is_user_photo:
                user_image_urls.append(raw_url)
            else:
                curated_image_urls.append(raw_url)

        # Format detailed response
        place_details = {
            'placeId': place.get('id', ''),
            'name': place.get('displayName', {}).get('text', ''),
            'formattedAddress': place.get('formattedAddress', ''),
            'location': {
                'latitude': place.get('location', {}).get('latitude'),
                'longitude': place.get('location', {}).get('longitude')
            },
            'types': place.get('types', []),
            'rating': place.get('rating'),
            'userRatingsTotal': place.get('userRatingCount'),
            'phoneNumber': place.get('internationalPhoneNumber', ''),
            'internationalPhoneNumber': place.get('internationalPhoneNumber', ''),
            'website': place.get('websiteUri', ''),
            'url': place.get('websiteUri', ''),  # URL for the place
            'editorialSummary': place.get('editorialSummary', {}).get('text', ''),
            'photos': photos,  # Array of photos with S3 URLs
            'curatedImageUrls': curated_image_urls,  # S3 URLs for curated photos
            'userImageUrls': user_image_urls,  # S3 URLs for user photos
            'photoAttributions': photo_attributions  # Attributions for each photo
        }

        logger.info(f"Place details fetched: {place_details['name']}, {len(photos)} photos uploaded to S3")
        return jsonify(place_details), 200

    except Exception as e:
        logger.error(f"Error fetching place details: {e}", exc_info=True)
        return jsonify({'error': f'Error fetching place details: {str(e)}'}), 500


@places_bp.route('/download-photo', methods=['POST'])
@jwt_required()
def download_and_upload_photo():
    """
    Download a photo from Google Places API (New) v1 and upload it to S3.

    JSON body:
        photo_reference (str): Google Places photo reference (photo 'name' from new API)
        max_width (int): Maximum width in pixels (default: 1600)
        filename_prefix (str): Prefix for S3 filename (default: "site")

    Returns:
        JSON with S3 URL of the uploaded image
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        photo_reference = data.get('photo_reference')
        max_width = data.get('max_width', 1600)
        filename_prefix = data.get('filename_prefix', 'site')

        if not photo_reference:
            return jsonify({'error': 'photo_reference is required'}), 400

        api_key = current_app.config.get('GOOGLE_API_KEY')
        if not api_key:
            return jsonify({'error': 'Google API key not configured'}), 500

        logger.info(f"Downloading Google Place photo: {photo_reference[:50]}...")

        # Use Places API (New) v1 photo endpoint
        # Photo reference in new API is the full resource name like "places/{place_id}/photos/{photo_id}"
        photo_url = f"https://places.googleapis.com/v1/{photo_reference}/media?key={api_key}&maxWidthPx={max_width}"

        # Download the photo
        response = requests.get(photo_url, timeout=30)

        if response.status_code != 200:
            logger.error(f"Failed to download photo: HTTP {response.status_code} - {response.text}")
            return jsonify({'error': f'Failed to download photo from Google: HTTP {response.status_code}'}), 502

        # Get content type
        content_type = response.headers.get('Content-Type', 'image/jpeg')

        # Determine file extension
        extension = 'jpg'
        if 'png' in content_type:
            extension = 'png'
        elif 'webp' in content_type:
            extension = 'webp'

        # Create a file-like object from the image bytes
        image_file = io.BytesIO(response.content)
        image_file.seek(0)

        # Generate filename from photo reference
        photo_id = photo_reference.split('/')[-1] if '/' in photo_reference else photo_reference
        filename = f"{filename_prefix}_{photo_id[:20]}.{extension}"

        logger.info(f"Uploading photo to S3: {filename}")

        # Upload to S3 using existing service
        s3_url = upload_file_to_s3(
            image_file,
            filename,
            content_type=content_type,
            folder='sites'
        )

        logger.info(f"Photo uploaded successfully: {s3_url}")

        return jsonify({
            'url': s3_url,
            'filename': filename,
            'photoReference': photo_reference
        }), 200

    except requests.RequestException as e:
        logger.error(f"Error downloading photo: {e}", exc_info=True)
        return jsonify({'error': f'Error downloading photo: {str(e)}'}), 502
    except Exception as e:
        logger.error(f"Error processing photo: {e}", exc_info=True)
        return jsonify({'error': f'Error processing photo: {str(e)}'}), 500
