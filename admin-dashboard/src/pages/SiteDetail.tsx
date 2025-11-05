import { useState, FormEvent, useEffect, useRef, useMemo } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import type { LeafletMouseEvent } from 'leaflet';
import { useAuth } from '../lib/auth';
import { sitesApi, uploadApi, adminAiApi } from '../lib/api';
import { usePresignedUrl, usePresignedUrls } from '../hooks/usePresignedUrl';
import FileUpload from '../components/FileUpload';
import type { Site } from '../types';

// Helper component to recenter map when coordinates change
function MapRecenter({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, map.getZoom());
  }, [center, map]);
  return null;
}

interface NavigationState {
  fromTour?: string;
  siteIndex?: number;
  totalSites?: number;
  siteIds?: string[];
}

export default function SiteDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { isAdmin } = useAuth();
  const isNew = id === 'new';

  // Get navigation state from location, with sessionStorage fallback
  const [navigationState, setNavigationState] = useState<NavigationState | null>(() => {
    // First try location.state
    if (location.state && (location.state as NavigationState).fromTour) {
      return location.state as NavigationState;
    }
    // Fallback to sessionStorage
    const stored = sessionStorage.getItem(`siteNav_${id}`);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return null;
      }
    }
    return null;
  });

  // Persist navigation state to sessionStorage when it changes
  useEffect(() => {
    if (location.state && (location.state as NavigationState).fromTour) {
      const navState = location.state as NavigationState;
      setNavigationState(navState);
      sessionStorage.setItem(`siteNav_${id}`, JSON.stringify(navState));
    }
  }, [location.state, id]);

  // Cleanup sessionStorage when component unmounts
  useEffect(() => {
    return () => {
      // Don't clean up immediately - allow navigation to work
      setTimeout(() => {
        const currentPath = window.location.pathname;
        if (!currentPath.includes('/sites/')) {
          sessionStorage.removeItem(`siteNav_${id}`);
        }
      }, 100);
    };
  }, [id]);

  const [formData, setFormData] = useState<Partial<Site>>({
    title: '',
    description: '',
    latitude: 0,
    longitude: 0,
    imageUrl: '',
    audioUrl: '',
    webUrl: '',
    keywords: [],
    formatted_address: '',
    types: [],
    phone_number: '',
  });
  const [originalData, setOriginalData] = useState<Partial<Site> | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [generatingAudio, setGeneratingAudio] = useState(false);
  const [generatingDescription, setGeneratingDescription] = useState(false);

  const descriptionRef = useRef<HTMLTextAreaElement>(null);

  const { data: siteData, isLoading } = useQuery({
    queryKey: ['site', id],
    queryFn: () => sitesApi.get(id!),
    enabled: !isNew && !!id,
  });

  useEffect(() => {
    if (siteData) {
      setFormData(siteData);
      setOriginalData(siteData);
      setHasUnsavedChanges(false);
    }
  }, [siteData]);

  useEffect(() => {
    if (originalData) {
      const changed = JSON.stringify(formData) !== JSON.stringify(originalData);
      setHasUnsavedChanges(changed);
    } else if (isNew) {
      // For new sites, check if any meaningful data has been entered
      const changed = formData.title !== '' || formData.description !== '';
      setHasUnsavedChanges(changed);
    }
  }, [formData, originalData, isNew]);

  // Auto-resize description textarea
  useEffect(() => {
    const textarea = descriptionRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  }, [formData.description]);

  // Presign S3 URLs for display
  const presignedImageUrl = usePresignedUrl(formData.imageUrl);
  const presignedAudioUrl = usePresignedUrl(formData.audioUrl);
  const presignedGooglePhotos = usePresignedUrls(formData.googlePhotoReferences || []);

  const saveMutation = useMutation({
    mutationFn: (data: Partial<Site>) =>
      isNew ? sitesApi.create(data) : sitesApi.update(id!, data),
    onSuccess: (savedSite) => {
      queryClient.invalidateQueries({ queryKey: ['sites'] });
      queryClient.invalidateQueries({ queryKey: ['site', id] });
      toast.success(isNew ? 'Site created!' : 'Site saved!');
      setOriginalData(savedSite);
      setHasUnsavedChanges(false);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to save site');
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
  };

  const handleSaveChanges = () => {
    if (!formData.title || formData.latitude === undefined || formData.longitude === undefined) {
      toast.error('Title, latitude, and longitude are required');
      return;
    }
    saveMutation.mutate(formData);
  };

  const handleSaveAndClose = () => {
    if (!formData.title || formData.latitude === undefined || formData.longitude === undefined) {
      toast.error('Title, latitude, and longitude are required');
      return;
    }
    saveMutation.mutate(formData, {
      onSuccess: () => {
        navigate('/sites');
      },
    });
  };

  const handleDiscardChanges = () => {
    if (originalData) {
      setFormData(originalData);
      setHasUnsavedChanges(false);
      toast.success('Changes discarded');
    } else if (isNew) {
      // Reset to empty state for new sites
      setFormData({
        title: '',
        description: '',
        latitude: 0,
        longitude: 0,
        imageUrl: '',
        audioUrl: '',
        webUrl: '',
        keywords: [],
        formatted_address: '',
        types: [],
        phone_number: '',
      });
      setHasUnsavedChanges(false);
      toast.success('Changes discarded');
    }
  };

  const handleDiscardAndClose = () => {
    navigate('/sites');
  };

  const handleBack = () => {
    if (hasUnsavedChanges) {
      if (window.confirm('You have unsaved changes. Are you sure you want to leave?')) {
        // Navigate back to tour if coming from tour, otherwise to sites list
        if (navigationState?.fromTour) {
          navigate(`/tours/${navigationState.fromTour}`);
        } else {
          navigate('/sites');
        }
      }
    } else {
      // Navigate back to tour if coming from tour, otherwise to sites list
      if (navigationState?.fromTour) {
        navigate(`/tours/${navigationState.fromTour}`);
      } else {
        navigate('/sites');
      }
    }
  };

  const handlePrevious = () => {
    if (!navigationState || navigationState.siteIndex === undefined || !navigationState.siteIds) return;

    if (hasUnsavedChanges) {
      if (!window.confirm('You have unsaved changes. Are you sure you want to leave?')) {
        return;
      }
    }

    const prevIndex = navigationState.siteIndex - 1;
    if (prevIndex >= 0) {
      const prevSiteId = navigationState.siteIds[prevIndex];
      navigate(`/sites/${prevSiteId}`, {
        state: {
          fromTour: navigationState.fromTour,
          siteIndex: prevIndex,
          totalSites: navigationState.totalSites,
          siteIds: navigationState.siteIds
        }
      });
    }
  };

  const handleNext = () => {
    if (!navigationState || navigationState.siteIndex === undefined || !navigationState.siteIds) return;

    if (hasUnsavedChanges) {
      if (!window.confirm('You have unsaved changes. Are you sure you want to leave?')) {
        return;
      }
    }

    const nextIndex = navigationState.siteIndex + 1;
    if (nextIndex < navigationState.siteIds.length) {
      const nextSiteId = navigationState.siteIds[nextIndex];
      navigate(`/sites/${nextSiteId}`, {
        state: {
          fromTour: navigationState.fromTour,
          siteIndex: nextIndex,
          totalSites: navigationState.totalSites,
          siteIds: navigationState.siteIds
        }
      });
    }
  };

  // Determine if we have previous/next navigation
  const isFromTour = !!navigationState?.fromTour;
  const hasPrevious = isFromTour && navigationState.siteIndex !== undefined && navigationState.siteIndex > 0;
  const hasNext = isFromTour && navigationState.siteIndex !== undefined && navigationState.totalSites !== undefined && navigationState.siteIndex < navigationState.totalSites - 1;

  const handleGenerateAudio = async () => {
    if (!formData.description || !formData.description.trim()) {
      toast.error('Please add a description first');
      return;
    }

    setGeneratingAudio(true);

    try {
      const result = await uploadApi.generateAudio(formData.description);
      updateField('audioUrl', result.url);
      toast.success(result.from_cache ? 'Audio retrieved from cache!' : 'Audio generated successfully!');
    } catch (error: any) {
      console.error('Generate audio error:', error);
      toast.error(error.response?.data?.error || 'Failed to generate audio');
    } finally {
      setGeneratingAudio(false);
    }
  };

  const handleGenerateDescription = async () => {
    if (!formData.title || !formData.latitude || !formData.longitude) {
      toast.error('Please add title and coordinates first');
      return;
    }

    setGeneratingDescription(true);

    try {
      const result = await adminAiApi.generateDescription({
        siteName: formData.title,
        latitude: formData.latitude,
        longitude: formData.longitude,
      });
      updateField('description', result.description);
      toast.success('AI description generated!');
    } catch (error: any) {
      console.error('Generate description error:', error);
      toast.error(error.response?.data?.error || 'Failed to generate description');
    } finally {
      setGeneratingDescription(false);
    }
  };

  const updateField = (field: keyof Site, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleMarkerDragEnd = (event: LeafletMouseEvent) => {
    const { lat, lng } = event.target.getLatLng();
    setFormData((prev) => ({
      ...prev,
      latitude: lat,
      longitude: lng,
    }));
    toast.success('Pin moved! Remember to save changes.');
  };

  // Memoize the map center to avoid unnecessary re-renders
  const mapCenter = useMemo(
    () => [formData.latitude || 0, formData.longitude || 0] as [number, number],
    [formData.latitude, formData.longitude]
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#8B6F47] mb-4"></div>
          <p className="text-gray-600 font-medium">Loading site...</p>
        </div>
      </div>
    );
  }


  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-gray-900">
            {isNew ? 'Create New Site' : formData.title || 'Untitled Site'}
          </h1>
          {hasUnsavedChanges && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
              Unsaved changes
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!isFromTour ? (
            /* Simple back button when not from tour */
            <button
              type="button"
              onClick={handleBack}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-lg transition-all"
            >
              ← Back
            </button>
          ) : (
            /* Tour navigation: always show 2 buttons + position indicator */
            <>
              {/* First button: "Back to Tour" on first site, "Previous" otherwise */}
              <button
                type="button"
                onClick={hasPrevious ? handlePrevious : handleBack}
                className="min-w-[140px] px-4 py-2 text-sm font-medium text-white bg-[#8B6F47] hover:bg-[#6F5838] rounded-lg transition-all md:min-w-0"
                title={hasPrevious ? "Previous site" : "Back to tour"}
              >
                <span className="hidden md:inline">{hasPrevious ? '← Previous' : '← Back to Tour'}</span>
                <span className="md:hidden">{hasPrevious ? '←' : '←←'}</span>
              </button>

              {/* Position indicator */}
              <span className="text-sm text-gray-600">
                {navigationState.siteIndex !== undefined && navigationState.totalSites ?
                  `${navigationState.siteIndex + 1} of ${navigationState.totalSites}` : ''}
              </span>

              {/* Second button: "Next" on last site becomes "Back to Tour", otherwise "Next" */}
              <button
                type="button"
                onClick={hasNext ? handleNext : handleBack}
                className="min-w-[140px] px-4 py-2 text-sm font-medium text-white bg-[#8B6F47] hover:bg-[#6F5838] rounded-lg transition-all md:min-w-0"
                title={hasNext ? "Next site" : "Back to tour"}
              >
                <span className="hidden md:inline">{hasNext ? 'Next →' : 'Back to Tour →'}</span>
                <span className="md:hidden">{hasNext ? '→' : '→→'}</span>
              </button>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content - Left Column */}
        <div className="lg:col-span-2">
          {/* Form */}
          <form id="site-form" onSubmit={handleSubmit} className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 overflow-hidden">
            <div className="p-8 pb-32 space-y-6">
            {/* Site Title */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Site Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.title}
                onChange={(e) => updateField('title', e.target.value)}
                placeholder="Enter site title..."
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                ref={descriptionRef}
                value={formData.description || ''}
                onChange={(e) => updateField('description', e.target.value)}
                placeholder="Describe the site..."
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white resize-none overflow-hidden disabled:bg-gray-100 disabled:cursor-not-allowed"
                style={{ minHeight: '120px' }}
              />
              <button
                type="button"
                onClick={handleGenerateDescription}
                disabled={!formData.title || !formData.latitude || !formData.longitude || generatingDescription}
                className="mt-2 w-full px-4 py-2.5 bg-[#8B6F47] hover:bg-[#6F5838] text-white text-sm font-medium rounded-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {generatingDescription ? (
                  <>
                    <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Generating Description...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    Generate Description with AI
                  </>
                )}
              </button>
            </div>

            {/* Audio */}
            <div>
              {presignedAudioUrl && (
                <audio controls className="mb-2 w-full">
                  <source src={presignedAudioUrl} />
                </audio>
              )}
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Audio URL
              </label>
              <div className="flex gap-2 mb-2">
                <input
                  type="url"
                  value={formData.audioUrl || ''}
                  onChange={(e) => updateField('audioUrl', e.target.value)}
                  placeholder="https://s3.amazonaws.com/..."
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
                <FileUpload
                  type="audio"
                  folder="sites/audio"
                  onUploadComplete={(url) => updateField('audioUrl', url)}
                  label="Upload Audio"
                  iconOnly
                />
              </div>
              <button
                type="button"
                onClick={handleGenerateAudio}
                disabled={!formData.description || generatingAudio}
                className="w-full px-4 py-2.5 bg-[#8B6F47] hover:bg-[#6F5838] text-white text-sm font-medium rounded-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {generatingAudio ? (
                  <>
                    <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Generating Audio...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                    Generate Audio from Description
                  </>
                )}
              </button>
            </div>

          {/* Coordinates Section */}
          <div className="space-y-4 pt-6 border-t border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-2xl">📐</span>
              Coordinates
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Latitude <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="any"
                  required
                  
                  value={formData.latitude}
                  onChange={(e) => updateField('latitude', parseFloat(e.target.value))}
                  placeholder="e.g., 37.7749"
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Longitude <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="any"
                  required
                  
                  value={formData.longitude}
                  onChange={(e) => updateField('longitude', parseFloat(e.target.value))}
                  placeholder="e.g., -122.4194"
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
              </div>
            </div>
          </div>

          {/* Location Section */}
          <div className="space-y-4 pt-6 border-t border-gray-200">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <span className="text-2xl">📍</span>
                {formData.neighborhood && formData.city
                  ? `${formData.neighborhood}, ${formData.city}`
                  : formData.city || formData.neighborhood || 'Location'}
              </h2>
              <p className="text-sm text-gray-500 mt-1 italic">
                Drag the pin to adjust coordinates
              </p>
            </div>

            {/* Map with draggable marker */}
            {formData.latitude && formData.longitude && (
              <div className="h-96 rounded-xl overflow-hidden border-2 border-gray-200">
                <MapContainer
                  center={mapCenter}
                  zoom={15}
                  style={{ height: '100%', width: '100%' }}
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <MapRecenter center={mapCenter} />
                  <Marker
                    position={mapCenter}
                    draggable={true}
                    eventHandlers={{
                      dragend: handleMarkerDragEnd,
                    }}
                  >
                    <Popup>
                      <div>
                        <strong className="font-semibold">{formData.title}</strong>
                        {formData.description && (
                          <p className="text-xs mt-1 line-clamp-2">{formData.description}</p>
                        )}
                        <p className="text-xs mt-2 text-gray-600 italic">Drag to move pin</p>
                      </div>
                    </Popup>
                  </Marker>
                </MapContainer>
              </div>
            )}
          </div>

          {/* Address and Contact Info */}
          <div className="space-y-4 pt-6 border-t border-gray-200">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Address
              </label>
              <input
                type="text"
                value={formData.formatted_address || ''}
                onChange={(e) => updateField('formatted_address', e.target.value)}
                placeholder="123 Main St, City, State"
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Phone Number
              </label>
              <input
                type="tel"
                value={formData.phone_number || ''}
                onChange={(e) => updateField('phone_number', e.target.value)}
                placeholder="+1 (555) 123-4567"
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Website
              </label>
              <input
                type="url"
                value={formData.webUrl || ''}
                onChange={(e) => updateField('webUrl', e.target.value)}
                placeholder="https://example.com"
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            </div>

            {/* Google Photos */}
            {formData.googlePhotoReferences && formData.googlePhotoReferences.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Google Photos
                </label>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {presignedGooglePhotos.map((photoUrl, index) => (
                    photoUrl && (
                      <div key={index} className="aspect-square rounded-lg overflow-hidden border-2 border-gray-200">
                        <img
                          src={photoUrl}
                          alt={`Google Photo ${index + 1}`}
                          className="w-full h-full object-cover hover:scale-110 transition-transform duration-200"
                        />
                      </div>
                    )
                  ))}
                </div>
              </div>
            )}
          </div>

            </div>
          </form>
        </div>

        {/* Information Sidebar - Right Column */}
        <div className="lg:col-span-1">
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 p-6 space-y-6 sticky top-20">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-2xl">ℹ️</span>
              Information
            </h2>

            <div className="space-y-4">
              {/* Image */}
              <div>
                {presignedImageUrl && (
                  <div className="mb-3 w-full rounded-lg overflow-hidden border-2 border-gray-200">
                    <img
                      src={presignedImageUrl}
                      alt="Site"
                      className="w-full h-auto"
                    />
                  </div>
                )}
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                  Image URL
                </label>
                <div className="flex gap-2">
                  <input
                    type="url"
                    value={formData.imageUrl || ''}
                    onChange={(e) => updateField('imageUrl', e.target.value)}
                    placeholder="https://s3.amazonaws.com/..."
                    className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white"
                  />
                  <FileUpload
                    type="image"
                    folder="sites/images"
                    onUploadComplete={(url) => updateField('imageUrl', url)}
                    label="Upload Image"
                    iconOnly
                  />
                </div>
              </div>
              {/* Place ID */}
              {siteData?.placeId && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
                    Google Place ID
                  </label>
                  <div className="text-sm text-gray-900 font-mono break-all">
                    {siteData.placeId}
                  </div>
                </div>
              )}

              {/* Timestamps */}
              {siteData && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
                      Created
                    </label>
                    <div className="text-sm text-gray-900">
                      {new Date(siteData.createdAt).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
                      Last Updated
                    </label>
                    <div className="text-sm text-gray-900">
                      {new Date(siteData.updatedAt).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Form Actions - Fixed Bottom */}
      <div className="fixed bottom-0 left-0 right-0 z-10 bg-[#F6EDD9]/95 backdrop-blur-lg border-t border-gray-200/50 pl-64 pr-6 py-4 shadow-lg">
        <div className="flex justify-center items-center">
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleDiscardChanges}
              disabled={!hasUnsavedChanges || saveMutation.isPending}
              className="px-5 py-2.5 text-sm font-medium text-gray-700 hover:text-gray-900 bg-white hover:bg-gray-50 border border-gray-300 rounded-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Discard Changes
            </button>
            <button
              type="button"
              onClick={handleSaveChanges}
              disabled={!hasUnsavedChanges || saveMutation.isPending}
              className="px-5 py-2.5 bg-[#8B6F47] hover:bg-[#6F5838] text-white text-sm font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {saveMutation.isPending ? (
                <span className="flex items-center gap-2">
                  <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Saving...
                </span>
              ) : (
                'Save Changes'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
