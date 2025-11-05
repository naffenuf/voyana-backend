import type { Tour, Site } from '../types'

export interface ValidationIssue {
  field: string
  label: string
  message: string
}

export interface SiteValidationGroup {
  siteId: string
  siteName: string
  issues: ValidationIssue[]
}

export interface ValidationSummary {
  isValid: boolean
  issueCount: number
  tourIssues: ValidationIssue[]
  siteIssues: SiteValidationGroup[]
}

/**
 * Validates tour-level required fields for iOS compatibility
 */
export function validateTour(tour: Tour | null): ValidationIssue[] {
  if (!tour) return []

  const issues: ValidationIssue[] = []

  if (!tour.name?.trim()) {
    issues.push({
      field: 'name',
      label: 'Tour Name',
      message: 'Tour name is required'
    })
  }

  if (!tour.description?.trim()) {
    issues.push({
      field: 'description',
      label: 'Description',
      message: 'Tour description is required'
    })
  }

  if (!tour.city?.trim()) {
    issues.push({
      field: 'city',
      label: 'City',
      message: 'City is required'
    })
  }

  if (!tour.neighborhood?.trim()) {
    issues.push({
      field: 'neighborhood',
      label: 'Neighborhood',
      message: 'Neighborhood is required'
    })
  }

  if (!tour.imageUrl?.trim()) {
    issues.push({
      field: 'imageUrl',
      label: 'Tour Image',
      message: 'Tour image is required'
    })
  }

  if (!tour.mapImageUrl?.trim()) {
    issues.push({
      field: 'mapImageUrl',
      label: 'Map Image',
      message: 'Map image is required'
    })
  }

  // Check if tour has at least 3 sites (minimum for complete tour)
  const siteCount = tour.siteCount || tour.sites?.length || 0
  if (siteCount === 0) {
    issues.push({
      field: 'sites',
      label: 'Sites',
      message: 'Tour must have at least one site'
    })
  } else if (siteCount < 3) {
    issues.push({
      field: 'sites',
      label: 'Sites',
      message: `Tour must have at least 3 sites (currently has ${siteCount})`
    })
  }

  return issues
}

/**
 * Validates site-level required fields for iOS compatibility
 */
export function validateSite(site: Site): ValidationIssue[] {
  const issues: ValidationIssue[] = []

  if (!site.title?.trim()) {
    issues.push({
      field: 'title',
      label: 'Site Title',
      message: 'Site title is required'
    })
  }

  if (!site.description?.trim()) {
    issues.push({
      field: 'description',
      label: 'Description',
      message: 'Site description is required'
    })
  }

  if (site.latitude === null || site.latitude === undefined) {
    issues.push({
      field: 'latitude',
      label: 'Latitude',
      message: 'Latitude is required'
    })
  }

  if (site.longitude === null || site.longitude === undefined) {
    issues.push({
      field: 'longitude',
      label: 'Longitude',
      message: 'Longitude is required'
    })
  }

  if (!site.formatted_address?.trim()) {
    issues.push({
      field: 'formatted_address',
      label: 'Address',
      message: 'Address is required'
    })
  }

  if (!site.city?.trim()) {
    issues.push({
      field: 'city',
      label: 'City',
      message: 'City is required'
    })
  }

  if (!site.imageUrl?.trim()) {
    issues.push({
      field: 'imageUrl',
      label: 'Site Image',
      message: 'Site image is required'
    })
  }

  if (!site.audioUrl?.trim()) {
    issues.push({
      field: 'audioUrl',
      label: 'Audio Narration',
      message: 'Audio narration is required'
    })
  }

  return issues
}

/**
 * Generates a complete validation summary for a tour and its sites
 */
export function getValidationSummary(
  tour: Tour | null,
  sites: Site[] = []
): ValidationSummary {
  const tourIssues = validateTour(tour)

  const siteIssues: SiteValidationGroup[] = sites
    .map(site => ({
      siteId: site.id,
      siteName: site.title || 'Untitled Site',
      issues: validateSite(site)
    }))
    .filter(group => group.issues.length > 0)

  const issueCount = tourIssues.length + siteIssues.reduce(
    (sum, group) => sum + group.issues.length,
    0
  )

  return {
    isValid: issueCount === 0,
    issueCount,
    tourIssues,
    siteIssues
  }
}
