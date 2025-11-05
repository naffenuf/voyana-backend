/**
 * Geospatial utility functions for calculating distances and tour radii
 */

import type { Tour, Site } from '../types';

/**
 * Calculate the distance between two points using the Haversine formula
 * @param lat1 Latitude of first point
 * @param lon1 Longitude of first point
 * @param lat2 Latitude of second point
 * @param lon2 Longitude of second point
 * @returns Distance in meters
 */
export function haversineDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371000; // Earth's radius in meters
  const φ1 = (lat1 * Math.PI) / 180;
  const φ2 = (lat2 * Math.PI) / 180;
  const Δφ = ((lat2 - lat1) * Math.PI) / 180;
  const Δλ = ((lon2 - lon1) * Math.PI) / 180;

  const a =
    Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
    Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
}

/**
 * Calculate the geographic center (centroid) of all sites in a tour
 * @param sites Array of sites with coordinates
 * @returns Center coordinates [lat, lng] or null if no valid sites
 */
export function calculateTourCenter(sites: Site[]): [number, number] | null {
  if (!sites || sites.length === 0) {
    return null;
  }

  let totalLat = 0;
  let totalLng = 0;
  let validSiteCount = 0;

  for (const site of sites) {
    if (site.latitude && site.longitude) {
      totalLat += site.latitude;
      totalLng += site.longitude;
      validSiteCount++;
    }
  }

  if (validSiteCount === 0) {
    return null;
  }

  return [totalLat / validSiteCount, totalLng / validSiteCount];
}

/**
 * Calculate the radius of a tour based on the average distance from center to all sites
 * @param tour Tour with sites
 * @returns Object with center coordinates and radius in meters
 */
export function calculateTourRadius(tour: Tour): number {
  // If tour has no sites, return default radius
  if (!tour.sites || tour.sites.length === 0) {
    return 500;
  }

  // Calculate the actual geographic center of all sites
  const center = calculateTourCenter(tour.sites);
  if (!center) {
    return 500;
  }

  const [centerLat, centerLng] = center;
  let totalDistance = 0;
  let validSiteCount = 0;

  // Calculate distance from calculated center to each site
  for (const site of tour.sites) {
    if (site.latitude && site.longitude) {
      const distance = haversineDistance(
        centerLat,
        centerLng,
        site.latitude,
        site.longitude
      );
      totalDistance += distance;
      validSiteCount++;
    }
  }

  // If no valid sites, return default
  if (validSiteCount === 0) {
    return 500;
  }

  // Calculate average distance
  const averageDistance = totalDistance / validSiteCount;

  // Add 30% buffer for visual appeal, minimum 100m
  const radius = Math.max(100, averageDistance * 1.3);

  return radius;
}

/**
 * Check if a tour's bounds intersect with a given bounding box (for viewport filtering)
 * @param tour Tour with center and calculated radius
 * @param bounds Bounding box { minLat, maxLat, minLng, maxLng }
 * @param radius Tour radius in meters
 * @returns True if tour intersects with bounds
 */
export function tourIntersectsBounds(
  tour: Tour,
  bounds: { minLat: number; maxLat: number; minLng: number; maxLng: number },
  radius: number
): boolean {
  if (!tour.latitude || !tour.longitude) {
    return false;
  }

  // Convert radius from meters to approximate degrees
  // At equator: 1 degree latitude ≈ 111km, 1 degree longitude ≈ 111km * cos(latitude)
  const latBuffer = radius / 111000;
  const lngBuffer = radius / (111000 * Math.cos((tour.latitude * Math.PI) / 180));

  const tourMinLat = tour.latitude - latBuffer;
  const tourMaxLat = tour.latitude + latBuffer;
  const tourMinLng = tour.longitude - lngBuffer;
  const tourMaxLng = tour.longitude + lngBuffer;

  // Check if bounding boxes intersect
  return !(
    tourMaxLat < bounds.minLat ||
    tourMinLat > bounds.maxLat ||
    tourMaxLng < bounds.minLng ||
    tourMinLng > bounds.maxLng
  );
}
