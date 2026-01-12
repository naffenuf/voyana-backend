"""
Map generation service for creating and saving route maps for tours.
Uses Google Maps Directions API to optimize routes between tour sites
and generates static map images with route overlays.
"""
import os
import io
import uuid
import logging
import googlemaps
import matplotlib.pyplot as plt
import requests
from PIL import Image
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from app.services.s3_service import upload_file_to_s3
from app.models.tour import Tour, TourSite
from app.models.site import Site
from app import db

# Set up logging
logger = logging.getLogger(__name__)

class MapGenerationService:
    """Service for generating route maps for tours"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Map Generation Service.

        Args:
            api_key: Google Maps API key (if None, will load from environment)
        """
        self.api_key = api_key
        self.maps_api_enabled = False

        if not self.api_key:
            # Try to get API key from environment variables
            self.api_key = os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("GOOGLE_API_KEY")

            # Try to load from file if environment variable not found
            if not self.api_key and os.path.exists(".google_api_key"):
                try:
                    with open(".google_api_key", "r") as f:
                        self.api_key = f.read().strip()
                    logger.info("Using Google API key from .google_api_key file")
                except Exception as e:
                    logger.error(f"Error reading .google_api_key file: {str(e)}")

        if not self.api_key:
            logger.error("Google Maps API key not found. Map generation will not function.")
        else:
            # Initialize the Google Maps client
            try:
                self.gmaps = googlemaps.Client(key=self.api_key)
                self.maps_api_enabled = True
                logger.info("Google Maps API initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Google Maps client: {str(e)}")

    def generate_tour_map(self, tour_id: str) -> Optional[str]:
        """
        Generate an optimized route map for a tour and store it in S3.

        Args:
            tour_id: ID of the tour to generate a map for

        Returns:
            S3 URL of the generated map image if successful, None otherwise
        """
        if not self.maps_api_enabled:
            logger.error("Google Maps API not enabled. Cannot generate map.")
            return None

        try:
            # Get tour and associated sites ordered by display_order
            tour = db.session.query(Tour).filter_by(id=uuid.UUID(tour_id)).first()
            if not tour:
                logger.error(f"Tour with ID {tour_id} not found")
                return None

            # Get tour sites in order
            tour_sites = db.session.query(TourSite, Site).join(
                Site, TourSite.site_id == Site.id
            ).filter(
                TourSite.tour_id == tour.id
            ).order_by(
                TourSite.display_order
            ).all()

            if not tour_sites or len(tour_sites) < 2:
                logger.warning(f"Tour {tour_id} has fewer than 2 sites, cannot generate route map")
                return None

            # Extract site coordinates
            waypoints = []
            for tour_site, site in tour_sites:
                if site.latitude is not None and site.longitude is not None:
                    waypoints.append({
                        "id": str(site.id),
                        "title": site.title,
                        "location": (float(site.latitude), float(site.longitude))
                    })

            if len(waypoints) < 2:
                logger.warning(f"Tour {tour_id} has fewer than 2 sites with valid coordinates")
                return None

            # Generate the route and map
            origin = waypoints[0]["location"]
            destination = waypoints[-1]["location"]

            # Intermediate waypoints (exclude origin and destination)
            intermediate_points = [
                {"lat": wp["location"][0], "lng": wp["location"][1]}
                for wp in waypoints[1:-1]
            ]

            # Get directions - disable waypoint optimization for ordered tours
            # When is_ordered=True, use creator's fixed sequence instead of optimizing
            route_result = self.gmaps.directions(
                origin=origin,
                destination=destination,
                waypoints=intermediate_points,
                optimize_waypoints=not tour.is_ordered,  # False for ordered tours, True otherwise
                mode="walking",  # Assume walking tours (can be parameterized later)
                departure_time=datetime.now()
            )

            if not route_result:
                logger.error(f"No route found for tour {tour_id}")
                return None

            # Create map visualization with the route
            map_image = self._create_map_visualization(route_result, waypoints)

            if not map_image:
                logger.error(f"Failed to create map visualization for tour {tour_id}")
                return None

            # Save the map image to S3
            image_buffer = io.BytesIO()
            map_image.save(image_buffer, format='PNG')
            image_buffer.seek(0)

            # Upload to S3 with a unique filename
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            random_id = str(uuid.uuid4())[:8]
            filename = f'tour-{tour_id}-{timestamp}-{random_id}.png'

            map_url = upload_file_to_s3(
                image_buffer.getvalue(),
                filename,
                folder='maps',
                content_type='image/png'
            )

            if not map_url:
                logger.error(f"Failed to upload map image to S3 for tour {tour_id}")
                return None

            # Update tour with map image URL
            tour.map_image_url = map_url
            db.session.commit()

            logger.info(f"Successfully generated map for tour {tour_id}, saved to {map_url}")
            return map_url

        except Exception as e:
            logger.error(f"Error generating map for tour {tour_id}: {str(e)}", exc_info=True)
            return None

    def _create_map_visualization(self, route_result: List[Dict[str, Any]], waypoints: List[Dict[str, Any]]) -> Optional[Image.Image]:
        """
        Create a map visualization with route overlay using Google Maps Static API.

        Args:
            route_result: Google Maps Directions API response
            waypoints: List of waypoints with coordinates

        Returns:
            PIL Image object containing the map visualization
        """
        try:
            if not route_result or not waypoints:
                return None

            # Extract overview polyline from route
            route = route_result[0]
            overview_polyline = route.get('overview_polyline', {}).get('points', '')

            # Calculate map center and zoom level
            waypoint_lats = [wp["location"][0] for wp in waypoints]
            waypoint_lngs = [wp["location"][1] for wp in waypoints]
            center_lat = (max(waypoint_lats) + min(waypoint_lats)) / 2
            center_lng = (max(waypoint_lngs) + min(waypoint_lngs)) / 2

            # Calculate appropriate zoom level
            lat_span = max(waypoint_lats) - min(waypoint_lats)
            lng_span = max(waypoint_lngs) - min(waypoint_lngs)
            max_span = max(lat_span, lng_span)

            # Determine zoom based on span
            # Zoom out by 1 level compared to legacy to ensure all markers are visible
            if max_span > 0.2: zoom = 10      # Was 11
            elif max_span > 0.1: zoom = 11    # Was 12
            elif max_span > 0.05: zoom = 12   # Was 13
            elif max_span > 0.02: zoom = 13   # Was 14
            elif max_span > 0.01: zoom = 14   # Was 15
            elif max_span > 0.005: zoom = 15  # Was 16
            else: zoom = 16                   # Was 17

            logger.info(f"Route span: {max_span}, setting zoom level to {zoom}")

            # Maximum size for Google Static Maps API
            map_width = 640
            map_height = 640

            # Build markers for waypoints (GREEN markers)
            markers = []
            for wp in waypoints:
                lat = wp["location"][0]
                lng = wp["location"][1]
                # Use app green color #2D7249
                marker = f"size:mid|color:0x2D7249|{lat},{lng}"
                markers.append(marker)

            # Construct the Google Maps Static API URL
            static_map_url = "https://maps.googleapis.com/maps/api/staticmap?"

            # Add basic parameters with scale=2 for higher quality
            static_map_url += f"center={center_lat},{center_lng}&zoom={zoom}&size={map_width}x{map_height}&scale=2"

            # Add map type (roadmap is the standard view)
            static_map_url += "&maptype=roadmap"

            # Add the path using the overview polyline (GREEN with opacity)
            # Use app green color #2D7249 with DD opacity (~87%)
            static_map_url += f"&path=weight:6|color:0x2D7249DD|enc:{overview_polyline}"

            # Add markers for each waypoint
            for marker in markers:
                static_map_url += f"&markers={marker}"

            # Add API key
            static_map_url += f"&key={self.api_key}"

            logger.info(f"Requesting Google Maps static image at zoom level {zoom}")

            # Request the static map image
            response = requests.get(static_map_url)
            if response.status_code != 200:
                raise Exception(f"Failed to get static map: HTTP {response.status_code}")

            # Convert response to PIL Image
            map_image = Image.open(io.BytesIO(response.content))

            # Return the map image
            return map_image

        except Exception as e:
            logger.error(f"Error creating map visualization with Google Maps: {str(e)}", exc_info=True)

            # Fallback to simple matplotlib visualization if Google Maps Static API fails
            try:
                logger.info("Falling back to simple map visualization")

                # Create a simple map with matplotlib
                fig, ax = plt.subplots(figsize=(10, 8))

                # Calculate boundaries
                waypoint_lats = [wp["location"][0] for wp in waypoints]
                waypoint_lngs = [wp["location"][1] for wp in waypoints]
                min_lat = min(waypoint_lats) - 0.005
                max_lat = max(waypoint_lats) + 0.005
                min_lng = min(waypoint_lngs) - 0.005
                max_lng = max(waypoint_lngs) + 0.005

                # Set map limits
                ax.set_xlim(min_lng, max_lng)
                ax.set_ylim(min_lat, max_lat)

                # Add a grid for reference
                ax.grid(alpha=0.3, linestyle='-')

                # Add background and styling
                ax.set_facecolor('#f5f5f0')
                plt.grid(color='#e0e0e0', linestyle='-', linewidth=0.7)

                # Extract route from each leg and plot
                route = route_result[0]
                for leg in route["legs"]:
                    for step in leg["steps"]:
                        points = self._decode_polyline(step["polyline"]["points"])
                        if points:
                            lats, lngs = zip(*points)
                            # Use app green color #2D7249
                            ax.plot(lngs, lats, color='#2D7249', linewidth=3.5, alpha=0.8, zorder=3)

                # Plot waypoints with green markers
                ax.scatter(
                    [wp["location"][1] for wp in waypoints],
                    [wp["location"][0] for wp in waypoints],
                    c='#2D7249', s=120, marker='o', edgecolor='white', linewidth=2.0, zorder=4
                )

                # Add waypoint labels
                for i, wp in enumerate(waypoints):
                    if "title" in wp:
                        ax.annotate(
                            wp['title'],
                            (wp["location"][1], wp["location"][0]),
                            xytext=(15, 0),
                            textcoords="offset points",
                            fontsize=10,
                            fontweight='bold',
                            color='black',
                            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#2D7249", alpha=0.9),
                            zorder=5,
                            arrowprops=dict(
                                arrowstyle="-",
                                connectionstyle="arc3,rad=0.1",
                                color="#2D7249",
                                shrinkA=0,
                                shrinkB=5,
                                alpha=0.7
                            )
                        )

                # Add title
                plt.title("Tour Route Map", fontsize=14, fontweight='bold')

                # Add north indicator
                plt.text(
                    0.98, 0.05, "N↑",
                    transform=ax.transAxes,
                    fontsize=12,
                    fontweight='bold',
                    ha='right',
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.7),
                    zorder=5
                )

                # Save to image
                img_buffer = io.BytesIO()
                plt.savefig(img_buffer, format='png', dpi=200, bbox_inches='tight')
                img_buffer.seek(0)
                plt.close()

                # Return as PIL Image
                return Image.open(img_buffer)

            except Exception as fallback_error:
                logger.error(f"Fallback map visualization also failed: {str(fallback_error)}", exc_info=True)
                return None

    def _decode_polyline(self, polyline_str: str) -> List[Tuple[float, float]]:
        """
        Decode Google Maps encoded polyline string into sequence of coordinates.

        Args:
            polyline_str: Encoded polyline string

        Returns:
            List of (latitude, longitude) coordinate tuples
        """
        try:
            index, lat, lng = 0, 0, 0
            coordinates = []

            while index < len(polyline_str):
                result = 1
                shift = 0

                # Decode latitude
                while True:
                    b = ord(polyline_str[index]) - 63 - 1
                    index += 1
                    result += b << shift
                    shift += 5
                    if b < 0x1f:
                        break

                lat += (~(result >> 1) if (result & 1) != 0 else (result >> 1))

                # Decode longitude
                result = 1
                shift = 0

                while True:
                    b = ord(polyline_str[index]) - 63 - 1
                    index += 1
                    result += b << shift
                    shift += 5
                    if b < 0x1f:
                        break

                lng += (~(result >> 1) if (result & 1) != 0 else (result >> 1))

                # Convert to decimal
                lat_float = lat * 1e-5
                lng_float = lng * 1e-5

                coordinates.append((lat_float, lng_float))

            return coordinates

        except Exception as e:
            logger.error(f"Error decoding polyline: {str(e)}", exc_info=True)
            return []


# Initialize a global instance
map_generation_service = MapGenerationService()
