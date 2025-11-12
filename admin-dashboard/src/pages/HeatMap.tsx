import { useState, useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { MapContainer, TileLayer, Circle, Tooltip, Marker, Popup, useMapEvents, useMap, ZoomControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';
import { adminToursApi, toursApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import { calculateTourRadius, calculateTourCenter, tourIntersectsBounds } from '../lib/geospatial';
import { MapPin, Filter, X } from 'lucide-react';
import type { Tour } from '../types';

// Extend Leaflet types for heat layer
declare module 'leaflet' {
  function heatLayer(
    latlngs: [number, number, number][],
    options?: any
  ): L.Layer;
}

interface TourWithRadius extends Tour {
  calculatedRadius: number;
  calculatedCenter: [number, number] | null;
}

// Component to add heat layer to map
function HeatLayer({ tours }: { tours: TourWithRadius[] }) {
  const map = useMap();

  useEffect(() => {
    if (!tours || tours.length === 0) return;

    // Prepare heat map data: [lat, lng, intensity]
    const heatData: [number, number, number][] = tours
      .filter((tour) => tour.calculatedCenter !== null)
      .map((tour) => [
        tour.calculatedCenter![0],
        tour.calculatedCenter![1],
        0.8, // Intensity (can be adjusted based on tour popularity, site count, etc.)
      ]);

    // Create heat layer with custom styling
    const heat = L.heatLayer(heatData, {
      radius: 25,
      blur: 15,
      maxZoom: 17,
      max: 1.0,
      gradient: {
        0.0: '#3B82F6', // Blue (low density)
        0.5: '#F59E0B', // Yellow (medium density)
        1.0: '#EF4444', // Red (high density)
      },
    });

    heat.addTo(map);

    return () => {
      map.removeLayer(heat);
    };
  }, [map, tours]);

  return null;
}

// Component to handle map bounds change for viewport filtering
function MapBoundsHandler({
  onBoundsChange,
}: {
  onBoundsChange: (bounds: {
    minLat: number;
    maxLat: number;
    minLng: number;
    maxLng: number;
  }) => void;
}) {
  const map = useMapEvents({
    moveend: () => {
      const bounds = map.getBounds();
      onBoundsChange({
        minLat: bounds.getSouth(),
        maxLat: bounds.getNorth(),
        minLng: bounds.getWest(),
        maxLng: bounds.getEast(),
      });

      // Save position to localStorage
      const center = map.getCenter();
      const zoom = map.getZoom();
      localStorage.setItem('heatMapPosition', JSON.stringify({
        lat: center.lat,
        lng: center.lng,
        zoom: zoom,
      }));
    },
  });

  return null;
}

// Component to auto-fit map bounds to show all tours
function AutoFitBounds({ tours }: { tours: TourWithRadius[] }) {
  const map = useMap();

  useEffect(() => {
    if (tours.length === 0) return;

    // Check if user has a saved position
    const savedPosition = localStorage.getItem('heatMapPosition');
    if (savedPosition) {
      try {
        const { lat, lng, zoom } = JSON.parse(savedPosition);
        map.setView([lat, lng], zoom);
        return;
      } catch (e) {
        // Invalid saved position, continue to auto-fit
      }
    }

    // Calculate bounding box from all tour centers
    const validCenters = tours
      .map(t => t.calculatedCenter)
      .filter((c): c is [number, number] => c !== null);

    if (validCenters.length === 0) return;

    // Create Leaflet LatLngBounds from tour centers
    const bounds = L.latLngBounds(validCenters);

    // Fit map to bounds with padding
    map.fitBounds(bounds, {
      padding: [50, 50], // 50px padding on all sides
      maxZoom: 15, // Don't zoom in too far even if there's only one tour
    });
  }, [map, tours]);

  return null;
}

export default function HeatMap() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [showFilters, setShowFilters] = useState(false);
  const [hoveredTourId, setHoveredTourId] = useState<string | null>(null);
  const [hoveredSiteId, setHoveredSiteId] = useState<string | null>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [mapBounds, setMapBounds] = useState<{
    minLat: number;
    maxLat: number;
    minLng: number;
    maxLng: number;
  } | null>(null);

  // Filter states
  const [statusFilter, setStatusFilter] = useState<string>('published');
  const [cityFilter, setCityFilter] = useState<string>('');
  const [neighborhoodFilter, setNeighborhoodFilter] = useState<string>('');

  // Fetch all tours with sites (admins see all, creators see their own)
  const { data: toursData, isLoading } = useQuery({
    queryKey: ['tours-heat-map', isAdmin, statusFilter, cityFilter, neighborhoodFilter],
    queryFn: () => {
      const filters = {
        status: statusFilter || undefined,
        city: cityFilter || undefined,
        neighborhood: neighborhoodFilter || undefined,
        limit: 10000, // Get all tours (can be paginated in future)
        include_sites: 'true', // Include full sites data for radius calculation
      };

      // Admins use admin API to see all tours
      // Creators use regular API which filters by owner
      return isAdmin ? adminToursApi.list(filters) : toursApi.list(filters);
    },
  });

  // Calculate radius and center for each tour
  const toursWithRadius = useMemo<TourWithRadius[]>(() => {
    if (!toursData?.tours) return [];

    return toursData.tours
      .map((tour) => {
        const calculatedCenter = tour.sites ? calculateTourCenter(tour.sites) : null;
        return {
          ...tour,
          calculatedRadius: calculateTourRadius(tour),
          calculatedCenter,
        };
      })
      .filter((tour) => tour.calculatedCenter !== null); // Only include tours with valid centers
  }, [toursData]);

  // Filter tours by current viewport bounds for rendering
  const visibleTours = useMemo(() => {
    if (!mapBounds) return toursWithRadius;

    return toursWithRadius.filter((tour) => {
      if (!tour.calculatedCenter) return false;

      // Create a temp tour object with calculatedCenter as lat/lng for bounds checking
      const tourForBoundsCheck = {
        ...tour,
        latitude: tour.calculatedCenter[0],
        longitude: tour.calculatedCenter[1],
      };

      return tourIntersectsBounds(tourForBoundsCheck, mapBounds, tour.calculatedRadius);
    });
  }, [toursWithRadius, mapBounds]);

  // Get unique cities and neighborhoods for filters
  const cities = useMemo(() => {
    if (!toursData?.tours) return [];
    const uniqueCities = new Set(
      toursData.tours.map((t) => t.city).filter((c): c is string => !!c)
    );
    return Array.from(uniqueCities).sort();
  }, [toursData]);

  const neighborhoods = useMemo(() => {
    if (!toursData?.tours) return [];
    const filtered = cityFilter
      ? toursData.tours.filter((t) => t.city === cityFilter)
      : toursData.tours;
    const uniqueNeighborhoods = new Set(
      filtered.map((t) => t.neighborhood).filter((n): n is string => !!n)
    );
    return Array.from(uniqueNeighborhoods).sort();
  }, [toursData, cityFilter]);

  // Default map center (will be overridden by AutoFitBounds or saved position)
  const defaultCenter: [number, number] = [40.7128, -74.006]; // NYC fallback

  const handleClearFilters = () => {
    setStatusFilter('published');
    setCityFilter('');
    setNeighborhoodFilter('');
  };

  return (
    <div className="fixed inset-0 pt-16 bg-gray-50">
      {/* Header Bar */}
      <div className="absolute top-16 left-0 right-0 z-[1000] bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <MapPin className="w-6 h-6 text-[#8B6F47]" />
          <h1 className="text-2xl font-bold text-gray-900">Tour Coverage Heat Map</h1>
        </div>

        <div className="flex items-center gap-4">
          {/* Tour count badge */}
          <div className="flex items-center gap-2 px-3 py-1 bg-[#F6EDD9] rounded-full">
            <span className="text-sm font-medium text-gray-700">
              {isLoading ? 'Loading...' : `${visibleTours.length} visible tours`}
            </span>
            {toursData && visibleTours.length !== toursWithRadius.length && (
              <span className="text-xs text-gray-500">
                (of {toursWithRadius.length} total)
              </span>
            )}
          </div>

          {/* Filters toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              showFilters
                ? 'bg-[#8B6F47] text-white'
                : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Filter className="w-4 h-4" />
            Filters
          </button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="absolute top-[120px] right-6 z-[1000] bg-white rounded-xl shadow-lg border border-gray-200 p-4 w-80">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Filters</h3>
            <button
              onClick={() => setShowFilters(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-3">
            {/* Status filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-[#8B6F47]"
              >
                <option value="">All</option>
                <option value="draft">Draft</option>
                <option value="ready">Ready for Review</option>
                <option value="published">Published</option>
                <option value="archived">Archived</option>
              </select>
            </div>

            {/* City filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                City
              </label>
              <select
                value={cityFilter}
                onChange={(e) => {
                  setCityFilter(e.target.value);
                  setNeighborhoodFilter(''); // Reset neighborhood when city changes
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-[#8B6F47]"
              >
                <option value="">All Cities</option>
                {cities.map((city) => (
                  <option key={city} value={city}>
                    {city}
                  </option>
                ))}
              </select>
            </div>

            {/* Neighborhood filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Neighborhood
              </label>
              <select
                value={neighborhoodFilter}
                onChange={(e) => setNeighborhoodFilter(e.target.value)}
                disabled={!cityFilter}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-[#8B6F47] disabled:bg-gray-100 disabled:cursor-not-allowed"
              >
                <option value="">All Neighborhoods</option>
                {neighborhoods.map((neighborhood) => (
                  <option key={neighborhood} value={neighborhood}>
                    {neighborhood}
                  </option>
                ))}
              </select>
            </div>

            {/* Clear filters button */}
            <button
              onClick={handleClearFilters}
              className="w-full px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 font-medium transition-colors"
            >
              Clear Filters
            </button>
          </div>
        </div>
      )}

      {/* Map Container */}
      <div className="w-full h-full">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#8B6F47] mx-auto mb-4"></div>
              <p className="text-gray-600">Loading tours...</p>
            </div>
          </div>
        ) : toursWithRadius.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <MapPin className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-xl font-medium text-gray-600">No tours found</p>
              <p className="text-gray-500 mt-2">Try adjusting your filters</p>
            </div>
          </div>
        ) : (
          <MapContainer
            center={defaultCenter}
            zoom={12}
            style={{ height: '100%', width: '100%' }}
            zoomControl={false}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {/* Zoom control positioned in bottom-right */}
            <ZoomControl position="bottomright" />

            {/* Auto-fit bounds to show all tours (or restore saved position) */}
            <AutoFitBounds tours={toursWithRadius} />

            {/* Heat layer for overall density visualization */}
            <HeatLayer tours={toursWithRadius} />

            {/* Map bounds handler for viewport filtering */}
            <MapBoundsHandler onBoundsChange={setMapBounds} />

            {/* Interactive circle markers for each tour */}
            {visibleTours.map((tour) => {
              if (!tour.calculatedCenter) return null;

              return (
                <Circle
                  key={tour.id}
                  center={tour.calculatedCenter}
                  radius={tour.calculatedRadius}
                  pathOptions={{
                    fillColor: '#8B6F47',
                    fillOpacity: hoveredTourId === tour.id ? 0.3 : 0.15,
                    color: hoveredTourId === tour.id ? '#944F2E' : '#8B6F47',
                    weight: hoveredTourId === tour.id ? 2 : 1,
                  }}
                  eventHandlers={{
                    mouseover: () => {
                      if (hoverTimeoutRef.current) {
                        clearTimeout(hoverTimeoutRef.current);
                      }
                      setHoveredTourId(tour.id);
                      setHoveredSiteId(null);
                    },
                    mouseout: () => {
                      // Delay clearing to allow child markers to capture hover
                      hoverTimeoutRef.current = setTimeout(() => {
                        setHoveredTourId(null);
                        setHoveredSiteId(null);
                      }, 50);
                    },
                    click: () => navigate(`/tours/${tour.id}`),
                  }}
                >
                  {/* Tooltip on hover */}
                  <Tooltip direction="top" offset={[0, -10]} opacity={0.75}>
                    <div style={{ backgroundColor: 'rgba(255, 255, 255, 0.85)' }}>
                      <strong className="font-semibold">{tour.name}</strong>
                      {tour.siteCount > 0 && (
                        <div className="text-xs text-gray-600 mt-1">
                          {tour.siteCount} sites • {Math.round(tour.calculatedRadius)}m radius
                        </div>
                      )}
                    </div>
                  </Tooltip>
                </Circle>
              );
            })}

            {/* Show individual sites when hovering over a tour */}
            {hoveredTourId && (() => {
              const hoveredTour = visibleTours.find(t => t.id === hoveredTourId);
              if (!hoveredTour || !hoveredTour.sites) return null;

              // Create custom icon for site markers - function to get icon based on hover state
              const getSiteIcon = (siteId: string) => {
                const isHovered = hoveredSiteId === siteId;
                return L.divIcon({
                  className: 'custom-site-marker',
                  html: `<div style="
                    width: ${isHovered ? '16px' : '12px'};
                    height: ${isHovered ? '16px' : '12px'};
                    background-color: #EF4444;
                    border: 2px solid white;
                    border-radius: 50%;
                    box-shadow: 0 2px ${isHovered ? '6px' : '4px'} rgba(0,0,0,${isHovered ? '0.5' : '0.3'});
                  "></div>`,
                  iconSize: [isHovered ? 16 : 12, isHovered ? 16 : 12],
                  iconAnchor: [isHovered ? 8 : 6, isHovered ? 8 : 6],
                });
              };

              // Create icon for tour center
              const isHoveredCenter = hoveredSiteId === 'center';
              const centerIcon = L.divIcon({
                className: 'custom-center-marker',
                html: `<div style="
                  width: ${isHoveredCenter ? '20px' : '16px'};
                  height: ${isHoveredCenter ? '20px' : '16px'};
                  background-color: #8B6F47;
                  border: 3px solid white;
                  border-radius: 50%;
                  box-shadow: 0 2px ${isHoveredCenter ? '8px' : '6px'} rgba(0,0,0,${isHoveredCenter ? '0.5' : '0.4'});
                "></div>`,
                iconSize: [isHoveredCenter ? 20 : 16, isHoveredCenter ? 20 : 16],
                iconAnchor: [isHoveredCenter ? 10 : 8, isHoveredCenter ? 10 : 8],
              });

              return (
                <>
                  {/* Tour center marker */}
                  {hoveredTour.calculatedCenter && (
                    <Marker
                      position={hoveredTour.calculatedCenter}
                      icon={centerIcon}
                      eventHandlers={{
                        mouseover: () => {
                          if (hoverTimeoutRef.current) {
                            clearTimeout(hoverTimeoutRef.current);
                          }
                          setHoveredTourId(hoveredTourId);
                          setHoveredSiteId('center');
                        },
                        mouseout: () => {
                          // Only clear site hover, let tour handle full clear
                          setHoveredSiteId(null);
                        }
                      }}
                    >
                      <Tooltip direction="top" offset={[0, -10]} opacity={0.75}>
                        <div style={{ backgroundColor: 'rgba(255, 255, 255, 0.85)' }}>
                          <strong className="font-semibold">Tour Center</strong>
                          <div className="text-xs text-gray-600 mt-1">
                            {hoveredTour.name}
                          </div>
                        </div>
                      </Tooltip>
                    </Marker>
                  )}

                  {/* Site markers */}
                  {hoveredTour.sites.map((site, index) => (
                    <Marker
                      key={site.id}
                      position={[site.latitude, site.longitude]}
                      icon={getSiteIcon(site.id)}
                      eventHandlers={{
                        mouseover: () => {
                          if (hoverTimeoutRef.current) {
                            clearTimeout(hoverTimeoutRef.current);
                          }
                          setHoveredTourId(hoveredTourId);
                          setHoveredSiteId(site.id);
                        },
                        mouseout: () => {
                          // Only clear site hover, let tour handle full clear
                          setHoveredSiteId(null);
                        }
                      }}
                    >
                      <Tooltip direction="top" offset={[0, -10]} opacity={0.75}>
                        <div style={{ backgroundColor: 'rgba(255, 255, 255, 0.85)' }}>
                          <strong className="font-semibold">{site.title}</strong>
                          {site.formatted_address && (
                            <div className="text-xs text-gray-600 mt-1">
                              {site.formatted_address.split(',')[0]}
                            </div>
                          )}
                        </div>
                      </Tooltip>
                    </Marker>
                  ))}
                </>
              );
            })()}
          </MapContainer>
        )}
      </div>
    </div>
  );
}
