import { useState, useEffect, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, Circle, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { toursApi } from '../lib/api';
import type { Tour, Site } from '../types';
import FileUpload from './FileUpload';

// Custom icons for different marker types
const WaypointIcon = L.divIcon({
  className: 'custom-waypoint-icon',
  html: '<div style="background-color: #8B6F47; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

// Create numbered site icon
const createNumberedSiteIcon = (number: number) => {
  return L.divIcon({
    className: 'custom-numbered-site-icon',
    html: `
      <div style="
        background-color: #3B82F6;
        color: white;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 2px 6px rgba(0,0,0,0.4);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 14px;
        font-family: system-ui, -apple-system, sans-serif;
      ">${number}</div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

interface DirectionsEditorPanelProps {
  tour: Tour;
  sites: Site[];
  disabled?: boolean;
}

interface EditableSegment {
  id?: string;
  directionText: string;
  audioUrl: string | null;
  triggerLatitude: number;
  triggerLongitude: number;
  triggerRadius: number;
}

interface TransitionData {
  fromSite: Site;
  toSite: Site;
  segments: EditableSegment[];
  isExpanded: boolean;
  isDirty: boolean;
}

export default function DirectionsEditorPanel({ tour, sites, disabled }: DirectionsEditorPanelProps) {
  const queryClient = useQueryClient();
  const mapRef = useRef<L.Map | null>(null);

  // State for transitions
  const [transitions, setTransitions] = useState<TransitionData[]>([]);
  const [selectedTransitionIndex, setSelectedTransitionIndex] = useState<number | null>(null);
  const [editingSegmentIndex, setEditingSegmentIndex] = useState<number | null>(null);

  // Fetch existing directions
  const { data: directionsData, isLoading } = useQuery({
    queryKey: ['tourDirections', tour.id],
    queryFn: () => toursApi.getDirections(tour.id),
    enabled: !!tour.id && tour.hasFixedDirections,
  });

  // Initialize transitions when sites or directions data changes
  useEffect(() => {
    if (sites.length < 2) {
      setTransitions([]);
      return;
    }

    const newTransitions: TransitionData[] = [];

    for (let i = 0; i < sites.length - 1; i++) {
      const fromSite = sites[i];
      const toSite = sites[i + 1];

      // Find existing segments for this transition
      const existingTransition = directionsData?.directions.find(
        (d) => d.fromSiteId === fromSite.id && d.toSiteId === toSite.id
      );

      const segments: EditableSegment[] = existingTransition
        ? existingTransition.segments.map((s) => ({
            id: s.id,
            directionText: s.directionText,
            audioUrl: s.audioUrl,
            triggerLatitude: s.triggerLatitude,
            triggerLongitude: s.triggerLongitude,
            triggerRadius: s.triggerRadius,
          }))
        : [];

      newTransitions.push({
        fromSite,
        toSite,
        segments,
        isExpanded: false,
        isDirty: false,
      });
    }

    setTransitions(newTransitions);
  }, [sites, directionsData]);

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async ({
      tourId,
      fromSiteId,
      toSiteId,
      segments,
    }: {
      tourId: string;
      fromSiteId: string;
      toSiteId: string;
      segments: EditableSegment[];
    }) => {
      return toursApi.upsertTransitionDirections(
        tourId,
        fromSiteId,
        toSiteId,
        segments.map((s) => ({
          directionText: s.directionText,
          audioUrl: s.audioUrl || undefined,
          triggerLatitude: s.triggerLatitude,
          triggerLongitude: s.triggerLongitude,
          triggerRadius: s.triggerRadius,
        }))
      );
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tourDirections', tour.id] });
      toast.success('Directions saved!');

      // Mark as not dirty
      setTransitions((prev) =>
        prev.map((t) =>
          t.fromSite.id === variables.fromSiteId && t.toSite.id === variables.toSiteId
            ? { ...t, isDirty: false }
            : t
        )
      );
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to save directions');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async ({
      tourId,
      fromSiteId,
      toSiteId,
    }: {
      tourId: string;
      fromSiteId: string;
      toSiteId: string;
    }) => {
      return toursApi.deleteTransitionDirections(tourId, fromSiteId, toSiteId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tourDirections', tour.id] });
      toast.success('Directions deleted');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to delete directions');
    },
  });

  // Map click handler component
  function MapClickHandler() {
    useMapEvents({
      click: (e) => {
        if (selectedTransitionIndex === null || disabled) return;

        const { lat, lng } = e.latlng;
        addWaypoint(selectedTransitionIndex, lat, lng);
      },
    });
    return null;
  }

  const addWaypoint = (transitionIndex: number, lat: number, lng: number) => {
    setTransitions((prev) => {
      const updated = [...prev];
      const transition = { ...updated[transitionIndex] };
      transition.segments = [
        ...transition.segments,
        {
          directionText: '',
          audioUrl: null,
          triggerLatitude: lat,
          triggerLongitude: lng,
          triggerRadius: 21,
        },
      ];
      transition.isDirty = true;
      updated[transitionIndex] = transition;
      return updated;
    });

    // Start editing the new segment
    const newSegmentIndex = transitions[transitionIndex].segments.length;
    setEditingSegmentIndex(newSegmentIndex);
  };

  const updateSegment = (transitionIndex: number, segmentIndex: number, updates: Partial<EditableSegment>) => {
    setTransitions((prev) => {
      const updated = [...prev];
      const transition = { ...updated[transitionIndex] };
      const segments = [...transition.segments];
      segments[segmentIndex] = { ...segments[segmentIndex], ...updates };
      transition.segments = segments;
      transition.isDirty = true;
      updated[transitionIndex] = transition;
      return updated;
    });
  };

  const deleteSegment = (transitionIndex: number, segmentIndex: number) => {
    setTransitions((prev) => {
      const updated = [...prev];
      const transition = { ...updated[transitionIndex] };
      transition.segments = transition.segments.filter((_, i) => i !== segmentIndex);
      transition.isDirty = true;
      updated[transitionIndex] = transition;
      return updated;
    });
    setEditingSegmentIndex(null);
  };

  const moveSegment = (transitionIndex: number, segmentIndex: number, direction: 'up' | 'down') => {
    setTransitions((prev) => {
      const updated = [...prev];
      const transition = { ...updated[transitionIndex] };
      const segments = [...transition.segments];

      const newIndex = direction === 'up' ? segmentIndex - 1 : segmentIndex + 1;
      if (newIndex < 0 || newIndex >= segments.length) return prev;

      [segments[segmentIndex], segments[newIndex]] = [segments[newIndex], segments[segmentIndex]];
      transition.segments = segments;
      transition.isDirty = true;
      updated[transitionIndex] = transition;
      return updated;
    });
  };

  const toggleTransition = (index: number) => {
    setTransitions((prev) =>
      prev.map((t, i) => (i === index ? { ...t, isExpanded: !t.isExpanded } : t))
    );
    if (!transitions[index].isExpanded) {
      setSelectedTransitionIndex(index);
    } else {
      setSelectedTransitionIndex(null);
    }
    setEditingSegmentIndex(null);
  };

  const saveTransition = (index: number) => {
    const transition = transitions[index];

    // Validate
    for (let i = 0; i < transition.segments.length; i++) {
      if (!transition.segments[i].directionText.trim()) {
        toast.error(`Waypoint ${i + 1} needs direction text`);
        return;
      }
    }

    saveMutation.mutate({
      tourId: tour.id,
      fromSiteId: transition.fromSite.id,
      toSiteId: transition.toSite.id,
      segments: transition.segments,
    });
  };

  const deleteAllSegments = (index: number) => {
    if (!confirm('Delete all waypoints for this transition?')) return;

    const transition = transitions[index];
    deleteMutation.mutate({
      tourId: tour.id,
      fromSiteId: transition.fromSite.id,
      toSiteId: transition.toSite.id,
    });

    setTransitions((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], segments: [], isDirty: false };
      return updated;
    });
  };

  // Calculate map center based on selected transition
  const getMapCenter = useCallback((): [number, number] => {
    if (selectedTransitionIndex !== null && transitions[selectedTransitionIndex]) {
      const t = transitions[selectedTransitionIndex];
      return [
        (t.fromSite.latitude + t.toSite.latitude) / 2,
        (t.fromSite.longitude + t.toSite.longitude) / 2,
      ];
    }
    if (sites.length > 0) {
      return [sites[0].latitude, sites[0].longitude];
    }
    return [40.7128, -74.006]; // NYC default
  }, [selectedTransitionIndex, transitions, sites]);

  // Get completion stats
  const completedTransitions = transitions.filter((t) => t.segments.length > 0).length;
  const totalTransitions = transitions.length;

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#8B6F47]"></div>
          <span className="ml-3 text-gray-600">Loading directions...</span>
        </div>
      </div>
    );
  }

  if (sites.length < 2) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Fixed Directions</h3>
        <p className="text-gray-500">Add at least 2 sites to create directions between them.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Fixed Directions</h3>
            <p className="text-sm text-gray-500">
              Create turn-by-turn directions between sites. Click on the map to place waypoints.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`px-3 py-1 rounded-full text-sm font-medium ${
                completedTransitions === totalTransitions
                  ? 'bg-green-100 text-green-800'
                  : 'bg-yellow-100 text-yellow-800'
              }`}
            >
              {completedTransitions}/{totalTransitions} transitions
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-gray-200">
        {/* Left: Transitions List */}
        <div className="p-4 max-h-[600px] overflow-y-auto">
          <div className="space-y-3">
            {transitions.map((transition, index) => (
              <div
                key={`${transition.fromSite.id}-${transition.toSite.id}`}
                className={`border rounded-lg overflow-hidden ${
                  selectedTransitionIndex === index ? 'border-[#8B6F47] ring-1 ring-[#8B6F47]' : 'border-gray-200'
                }`}
              >
                {/* Transition Header */}
                <button
                  type="button"
                  onClick={() => toggleTransition(index)}
                  className="w-full p-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center justify-center w-5 h-5 bg-blue-500 text-white text-xs font-bold rounded-full">
                      {index + 1}
                    </span>
                    <span className="font-medium text-gray-900 text-sm">
                      {transition.fromSite.title}
                    </span>
                    <span className="text-gray-400">→</span>
                    <span className="inline-flex items-center justify-center w-5 h-5 bg-blue-500 text-white text-xs font-bold rounded-full">
                      {index + 2}
                    </span>
                    <span className="font-medium text-gray-900 text-sm">{transition.toSite.title}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {transition.segments.length > 0 && (
                      <span className="px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded-full">
                        {transition.segments.length} waypoint{transition.segments.length !== 1 ? 's' : ''}
                      </span>
                    )}
                    {transition.isDirty && (
                      <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                        unsaved
                      </span>
                    )}
                    <svg
                      className={`w-5 h-5 text-gray-400 transition-transform ${
                        transition.isExpanded ? 'rotate-180' : ''
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </button>

                {/* Expanded Content */}
                {transition.isExpanded && (
                  <div className="p-3 border-t border-gray-200 space-y-3">
                    {transition.segments.length === 0 ? (
                      <p className="text-sm text-gray-500 text-center py-4">
                        Click on the map to add the first waypoint
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {transition.segments.map((segment, segIndex) => (
                          <div
                            key={segIndex}
                            className={`p-3 rounded-lg border ${
                              editingSegmentIndex === segIndex
                                ? 'border-[#8B6F47] bg-[#8B6F47]/5'
                                : 'border-gray-200 bg-white'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2 mb-2">
                              <span className="text-xs font-medium text-gray-500">
                                Waypoint {segIndex + 1}
                              </span>
                              <div className="flex items-center gap-1">
                                {segIndex > 0 && (
                                  <button
                                    type="button"
                                    onClick={() => moveSegment(index, segIndex, 'up')}
                                    className="p-1 text-gray-400 hover:text-gray-600"
                                    title="Move up"
                                  >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                                    </svg>
                                  </button>
                                )}
                                {segIndex < transition.segments.length - 1 && (
                                  <button
                                    type="button"
                                    onClick={() => moveSegment(index, segIndex, 'down')}
                                    className="p-1 text-gray-400 hover:text-gray-600"
                                    title="Move down"
                                  >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                  </button>
                                )}
                                <button
                                  type="button"
                                  onClick={() => deleteSegment(index, segIndex)}
                                  className="p-1 text-red-400 hover:text-red-600"
                                  title="Delete waypoint"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                  </svg>
                                </button>
                              </div>
                            </div>

                            <textarea
                              value={segment.directionText}
                              onChange={(e) => updateSegment(index, segIndex, { directionText: e.target.value })}
                              onFocus={() => setEditingSegmentIndex(segIndex)}
                              placeholder="E.g., Turn left at the fountain and continue toward the red building"
                              className="w-full p-2 text-sm border border-gray-200 rounded-lg resize-none focus:ring-1 focus:ring-[#8B6F47] focus:border-[#8B6F47]"
                              rows={2}
                              disabled={disabled}
                            />

                            <div className="flex items-center justify-between mt-2">
                              <div className="flex items-center gap-2">
                                <label className="text-xs text-gray-500">Radius:</label>
                                <input
                                  type="range"
                                  min={15}
                                  max={50}
                                  value={segment.triggerRadius}
                                  onChange={(e) =>
                                    updateSegment(index, segIndex, { triggerRadius: parseInt(e.target.value) })
                                  }
                                  className="w-20 h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[#8B6F47]"
                                  disabled={disabled}
                                />
                                <span className="text-xs text-gray-600">{segment.triggerRadius}m</span>
                              </div>

                              <div className="flex items-center gap-2">
                                {segment.audioUrl ? (
                                  <button
                                    type="button"
                                    onClick={() => updateSegment(index, segIndex, { audioUrl: null })}
                                    className="text-xs text-red-600 hover:text-red-700"
                                  >
                                    Remove audio
                                  </button>
                                ) : (
                                  <FileUpload
                                    type="audio"
                                    folder={`directions/${tour.id}`}
                                    onUploadComplete={(url) => updateSegment(index, segIndex, { audioUrl: url })}
                                    label="Add audio"
                                    className="text-xs"
                                    iconOnly
                                    uniqueId={`audio-${index}-${segIndex}`}
                                  />
                                )}
                                {segment.audioUrl && (
                                  <span className="text-xs text-green-600">Has audio</span>
                                )}
                              </div>
                            </div>

                            <div className="text-xs text-gray-400 mt-1">
                              {segment.triggerLatitude.toFixed(6)}, {segment.triggerLongitude.toFixed(6)}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex items-center justify-between pt-2 border-t border-gray-100">
                      <button
                        type="button"
                        onClick={() => deleteAllSegments(index)}
                        disabled={transition.segments.length === 0 || disabled || deleteMutation.isPending}
                        className="text-sm text-red-600 hover:text-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Clear all
                      </button>
                      <button
                        type="button"
                        onClick={() => saveTransition(index)}
                        disabled={!transition.isDirty || disabled || saveMutation.isPending}
                        className="px-3 py-1.5 bg-[#8B6F47] text-white text-sm font-medium rounded-lg hover:bg-[#6F5838] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {saveMutation.isPending ? 'Saving...' : 'Save'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Right: Map */}
        <div className="h-[600px]">
          <MapContainer
            center={getMapCenter()}
            zoom={16}
            className="h-full w-full"
            ref={mapRef}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <MapClickHandler />

            {/* Site markers with numbers */}
            {sites.map((site, index) => (
              <Marker
                key={site.id}
                position={[site.latitude, site.longitude]}
                icon={createNumberedSiteIcon(index + 1)}
              />
            ))}

            {/* Waypoint markers and circles for selected transition */}
            {selectedTransitionIndex !== null && transitions[selectedTransitionIndex] && (
              <>
                {/* Draw line between from and to sites */}
                <Polyline
                  positions={[
                    [
                      transitions[selectedTransitionIndex].fromSite.latitude,
                      transitions[selectedTransitionIndex].fromSite.longitude,
                    ],
                    ...transitions[selectedTransitionIndex].segments.map((s) => [
                      s.triggerLatitude,
                      s.triggerLongitude,
                    ] as [number, number]),
                    [
                      transitions[selectedTransitionIndex].toSite.latitude,
                      transitions[selectedTransitionIndex].toSite.longitude,
                    ],
                  ]}
                  color="#8B6F47"
                  weight={3}
                  opacity={0.7}
                  dashArray="5, 10"
                />

                {/* Waypoint markers */}
                {transitions[selectedTransitionIndex].segments.map((segment, segIndex) => (
                  <div key={segIndex}>
                    <Circle
                      center={[segment.triggerLatitude, segment.triggerLongitude]}
                      radius={segment.triggerRadius}
                      pathOptions={{
                        color: editingSegmentIndex === segIndex ? '#8B6F47' : '#69626d',
                        fillColor: editingSegmentIndex === segIndex ? '#8B6F47' : '#69626d',
                        fillOpacity: 0.2,
                      }}
                    />
                    <Marker
                      position={[segment.triggerLatitude, segment.triggerLongitude]}
                      icon={WaypointIcon}
                      eventHandlers={{
                        click: () => setEditingSegmentIndex(segIndex),
                      }}
                    />
                  </div>
                ))}
              </>
            )}
          </MapContainer>
        </div>
      </div>
    </div>
  );
}
