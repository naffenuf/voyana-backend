import { useMemo } from 'react'
import type { Tour, Site } from '../types'
import { getValidationSummary, type ValidationSummary } from '../lib/validation'

/**
 * Hook that provides real-time validation status for a tour and its sites
 */
export function useValidation(
  tour: Tour | null | undefined,
  sites: Site[] = []
): ValidationSummary {
  return useMemo(
    () => getValidationSummary(tour || null, sites || []),
    [tour, sites]
  )
}
