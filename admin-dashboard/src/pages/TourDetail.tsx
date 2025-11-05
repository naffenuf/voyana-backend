import { useState, FormEvent, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { toursApi, adminToursApi, sitesApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import { usePresignedUrl, usePresignedUrls } from '../hooks/usePresignedUrl';
import { useValidation } from '../hooks/useValidation';
import FileUpload from '../components/FileUpload';
import AddSiteWizard from '../components/AddSiteWizard';
import RemoveSiteDialog from '../components/RemoveSiteDialog';
import ValidationReportModal from '../components/ValidationReportModal';
import type { Tour, Site } from '../types';

export default function TourDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, isAdmin } = useAuth();
  const isNew = id === 'new';

  const [formData, setFormData] = useState<Partial<Tour>>({
    name: '',
    description: '',
    status: 'draft',
    imageUrl: '',
    mapImageUrl: '',
    musicUrls: [],
    durationMinutes: undefined,
    distanceMeters: undefined,
  });
  const [originalData, setOriginalData] = useState<Partial<Tour> | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [hoveredSiteId, setHoveredSiteId] = useState<string | null>(null);
  const [showAddSiteWizard, setShowAddSiteWizard] = useState(false);
  const [siteToRemove, setSiteToRemove] = useState<Site | null>(null);
  const [showValidationReport, setShowValidationReport] = useState(false);
  const descriptionRef = useRef<HTMLTextAreaElement>(null);
  const [playingIndex, setPlayingIndex] = useState<number | null>(null);
  const audioRefs = useRef<(HTMLAudioElement | null)[]>([]);

  const { data: tourData, isLoading } = useQuery({
    queryKey: ['tour', id],
    queryFn: () => toursApi.get(id!),
    enabled: !isNew && !!id,
  });

  useEffect(() => {
    if (tourData) {
      setFormData(tourData);
      setOriginalData(tourData);
      setHasUnsavedChanges(false);
    }
  }, [tourData]);

  useEffect(() => {
    if (originalData) {
      const changed = JSON.stringify(formData) !== JSON.stringify(originalData);
      setHasUnsavedChanges(changed);
    } else if (isNew) {
      // For new tours, check if any meaningful data has been entered
      const changed = formData.name !== '' || formData.description !== '';
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
  const presignedMapImageUrl = usePresignedUrl(formData.mapImageUrl);

  // Get presigned URLs for music tracks (using plural hook for arrays)
  const presignedMusicUrls = usePresignedUrls(formData.musicUrls || []);

  // Validation hook - checks tour and sites for required fields
  const validation = useValidation(tourData, tourData?.sites);

  // Create custom map icons
  const createIcon = (number: number, isHovered: boolean) => {
    const color = isHovered ? '#8B6F47' : '#3B82F6'; // Brown when hovered, blue otherwise
    const svg = `
      <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <circle cx="16" cy="16" r="14" fill="${color}" stroke="white" stroke-width="2"/>
        <text x="16" y="20" text-anchor="middle" font-size="14" font-weight="bold" fill="white">${number}</text>
      </svg>
    `;
    return L.divIcon({
      html: svg,
      className: 'custom-map-marker',
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    });
  };

  const saveMutation = useMutation({
    mutationFn: (data: Partial<Tour>) =>
      isNew ? toursApi.create(data) : toursApi.update(id!, data),
    onSuccess: (savedTour) => {
      queryClient.invalidateQueries({ queryKey: ['tours'] });
      queryClient.invalidateQueries({ queryKey: ['tour', id] });
      toast.success(isNew ? 'Tour created!' : 'Tour saved!');
      setOriginalData(savedTour);
      setHasUnsavedChanges(false);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to save tour');
    },
  });

  const generateAudioMutation = useMutation({
    mutationFn: () => toursApi.generateAudioForSites(id!),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['tour', id] });
      const successCount = result.sitesProcessed;
      const skippedCount = result.sitesSkipped;
      const errorCount = result.results.filter(r => r.status === 'error').length;

      let message = `Audio generation complete! `;
      if (successCount > 0) message += `${successCount} site(s) processed. `;
      if (skippedCount > 0) message += `${skippedCount} site(s) skipped. `;
      if (errorCount > 0) message += `${errorCount} error(s).`;

      if (errorCount > 0) {
        toast.error(message);
      } else {
        toast.success(message);
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to generate audio for sites');
    },
  });


  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
  };

  const handleSaveChanges = () => {
    if (!formData.name) {
      toast.error('Tour name is required');
      return;
    }

    // Filter out empty music URLs before saving
    const cleanedData = {
      ...formData,
      musicUrls: formData.musicUrls?.filter(url => url && url.trim() !== '') || []
    };

    saveMutation.mutate(cleanedData);
  };

  const handleSaveAndClose = () => {
    if (!formData.name) {
      toast.error('Tour name is required');
      return;
    }

    // Filter out empty music URLs before saving
    const cleanedData = {
      ...formData,
      musicUrls: formData.musicUrls?.filter(url => url && url.trim() !== '') || []
    };

    saveMutation.mutate(cleanedData, {
      onSuccess: () => {
        navigate('/tours');
      },
    });
  };

  const handleDiscardChanges = () => {
    if (originalData) {
      setFormData(originalData);
      setHasUnsavedChanges(false);
      toast.success('Changes discarded');
    } else if (isNew) {
      // Reset to empty state for new tours
      setFormData({
        name: '',
        description: '',
        status: 'draft',
        imageUrl: '',
        mapImageUrl: '',
        musicUrls: [],
        durationMinutes: undefined,
        distanceMeters: undefined,
      });
      setHasUnsavedChanges(false);
      toast.success('Changes discarded');
    }
  };

  const handleDiscardAndClose = () => {
    navigate('/tours');
  };

  const handleBack = () => {
    if (hasUnsavedChanges) {
      if (window.confirm('You have unsaved changes. Are you sure you want to leave?')) {
        navigate('/tours');
      }
    } else {
      navigate('/tours');
    }
  };

  const updateField = (field: keyof Tour, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const addMusicUrl = () => {
    const musicUrls = formData.musicUrls || [];
    setFormData((prev) => ({ ...prev, musicUrls: [...musicUrls, ''] }));
  };

  const updateMusicUrl = (index: number, value: string) => {
    const musicUrls = [...(formData.musicUrls || [])];
    musicUrls[index] = value;
    setFormData((prev) => ({ ...prev, musicUrls }));
  };

  const removeMusicUrl = (index: number) => {
    const musicUrls = [...(formData.musicUrls || [])];
    musicUrls.splice(index, 1);
    setFormData((prev) => ({ ...prev, musicUrls }));
  };

  const togglePlayPause = async (index: number) => {
    const audio = audioRefs.current[index];
    if (!audio) return;

    if (playingIndex === index) {
      audio.pause();
      setPlayingIndex(null);
    } else {
      // Pause any currently playing audio
      audioRefs.current.forEach((a, i) => {
        if (a && i !== index) a.pause();
      });

      try {
        await audio.play();
        setPlayingIndex(index);
      } catch (error) {
        console.error('Error playing audio:', error);
        toast.error('Failed to play audio. The file might not be accessible.');
      }
    }
  };

  const handleSiteCreated = (site: Site) => {
    // Refresh tour data to include the new site
    queryClient.invalidateQueries({ queryKey: ['tour', id] });
    toast.success(`Site "${site.title}" added to tour!`);
  };

  const handleRemoveFromTour = async () => {
    if (!siteToRemove || !tourData) return;

    try {
      // Get current site IDs and remove the selected one
      const currentSiteIds = tourData.siteIds || [];
      const updatedSiteIds = currentSiteIds.filter((siteId) => siteId !== siteToRemove.id);

      // Update the tour with the new site list
      await toursApi.update(id!, { siteIds: updatedSiteIds });

      // Refresh tour data
      queryClient.invalidateQueries({ queryKey: ['tour', id] });
      toast.success(`Site "${siteToRemove.title}" removed from tour`);
      setSiteToRemove(null);
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Failed to remove site from tour');
    }
  };

  const handleDeleteSite = async () => {
    if (!siteToRemove) return;

    try {
      await sitesApi.delete(siteToRemove.id);

      // Refresh tour data (site will be automatically removed)
      queryClient.invalidateQueries({ queryKey: ['tour', id] });
      queryClient.invalidateQueries({ queryKey: ['sites'] });
      toast.success(`Site "${siteToRemove.title}" deleted permanently`);
      setSiteToRemove(null);
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Failed to delete site');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#8B6F47] mb-4"></div>
          <p className="text-gray-600 font-medium">Loading tour...</p>
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
            {isNew ? 'Create New Tour' : formData.name || 'Untitled Tour'}
          </h1>
          {hasUnsavedChanges && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
              Unsaved changes
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={handleBack}
          className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-lg transition-all"
        >
          ← Back
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content - Left Column */}
        <div className="lg:col-span-2">
          {/* Edit Lock Warning */}
          {!isAdmin && formData.status === 'ready' && (
            <div className="bg-amber-50 border-l-4 border-amber-400 p-4 mb-6 rounded-lg">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <span className="text-2xl">⚠️</span>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-semibold text-amber-800">Tour Under Review</h3>
                  <p className="text-sm text-amber-700 mt-1">
                    This tour is currently under review and cannot be edited. An admin will either publish it or return it to draft status.
                  </p>
                </div>
              </div>
            </div>
          )}
          <form id="tour-form" onSubmit={handleSubmit} className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 overflow-hidden">
            <div className="p-8 pb-32 space-y-6">
              {/* Tour Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Tour Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => updateField('name', e.target.value)}
                  placeholder="Enter tour name..."
                  disabled={!isAdmin && formData.status === 'ready'}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>

              {/* Image and Map Side by Side */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Image */}
                <div>
                  {presignedImageUrl && (
                    <img src={presignedImageUrl} alt="Tour" className="w-full h-48 rounded-lg object-cover mb-2" />
                  )}
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Image URL
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="url"
                      value={formData.imageUrl || ''}
                      onChange={(e) => updateField('imageUrl', e.target.value)}
                      placeholder="https://s3.amazonaws.com/..."
                      className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white"
                    />
                    <FileUpload
                      type="image"
                      folder="tours/images"
                      onUploadComplete={(url) => updateField('imageUrl', url)}
                      label="Upload Image"
                      iconOnly
                    />
                  </div>
                </div>

                {/* Map */}
                <div>
                  {presignedMapImageUrl && (
                    <img src={presignedMapImageUrl} alt="Map" className="w-full h-48 rounded-lg object-cover mb-2" />
                  )}
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Map Image URL
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="url"
                      value={formData.mapImageUrl || ''}
                      onChange={(e) => updateField('mapImageUrl', e.target.value)}
                      placeholder="https://s3.amazonaws.com/..."
                      className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white"
                    />
                    <FileUpload
                      type="image"
                      folder="tours/maps"
                      onUploadComplete={(url) => updateField('mapImageUrl', url)}
                      label="Upload Map Image"
                      iconOnly
                    />
                  </div>
                </div>
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
                  placeholder="Describe the tour..."
                  disabled={!isAdmin && formData.status === 'ready'}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white resize-none overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ minHeight: '120px' }}
                />
              </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Background Music URLs
                    </label>
                    <button
                      type="button"
                      onClick={addMusicUrl}
                      className="text-sm text-blue-600 hover:text-blue-700 px-3 py-2"
                    >
                      + Add URL
                    </button>
                  </div>
                  <div className="space-y-2">
                    {(formData.musicUrls || []).map((url, index) => (
                      <div key={`music-url-${index}`} className="flex gap-2">
                          {url && (
                            <>
                              <button
                                type="button"
                                onClick={() => togglePlayPause(index)}
                                disabled={!url}
                                className="w-10 h-10 flex items-center justify-center text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-30"
                                title={playingIndex === index ? 'Pause' : 'Play'}
                              >
                                {playingIndex === index ? (
                                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
                                  </svg>
                                ) : (
                                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M8 5v14l11-7z"/>
                                  </svg>
                                )}
                              </button>
                              <audio
                                ref={(el) => (audioRefs.current[index] = el)}
                                src={presignedMusicUrls[index] || url}
                                crossOrigin="anonymous"
                                preload="metadata"
                                onEnded={() => setPlayingIndex(null)}
                                onError={(e) => console.error('Audio error:', e)}
                              />
                            </>
                          )}
                          <input
                            type="url"
                            value={url}
                            onChange={(e) => updateMusicUrl(index, e.target.value)}
                            placeholder="https://s3.amazonaws.com/..."
                            className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white"
                          />
                          <FileUpload
                            type="audio"
                            folder="tours/music"
                            onUploadComplete={(newUrl) => updateMusicUrl(index, newUrl)}
                            label="Upload Audio"
                            iconOnly
                            uniqueId={`music-upload-${index}`}
                          />
                          <button
                            type="button"
                            onClick={() => removeMusicUrl(index)}
                            className="w-10 h-10 flex items-center justify-center text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            ✕
                          </button>
                        </div>
                    ))}
                  </div>
                </div>

              {/* Location Section */}
              <div className="space-y-4 pt-6 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                      <span className="text-2xl">📍</span>
                      {formData.neighborhood && formData.city
                        ? `${formData.neighborhood}, ${formData.city}`
                        : formData.city || formData.neighborhood || 'Location'}
                    </h2>
                    {tourData?.sites && tourData.sites.length > 0 && (
                      <p className="text-sm text-gray-500 mt-1 italic">
                        Order optimized for user's location
                      </p>
                    )}
                  </div>
                  {!isNew && (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => generateAudioMutation.mutate()}
                        disabled={!tourData?.sites || tourData.sites.length === 0 || generateAudioMutation.isPending || (!isAdmin && formData.status === 'ready')}
                        className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors flex items-center gap-2 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Generate audio for all sites that don't have audio"
                      >
                        {generateAudioMutation.isPending ? (
                          <>
                            <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                            Generating...
                          </>
                        ) : (
                          <>
                            <span className="text-lg">🎵</span>
                            Generate Audio for Sites
                          </>
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowAddSiteWizard(true)}
                        disabled={!isAdmin && formData.status === 'ready'}
                        className="px-4 py-2 bg-[#8B6F47] hover:bg-[#6F5838] text-white rounded-lg transition-colors flex items-center gap-2 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <span className="text-lg">+</span>
                        Add Site
                      </button>
                    </div>
                  )}
                </div>

                {/* Map of tour sites */}
                {tourData?.sites && tourData.sites.length > 0 && (
                  <>
                    <div className="h-96 rounded-xl overflow-hidden border-2 border-gray-200">
                      <MapContainer
                        bounds={tourData.sites.map(site => [site.latitude, site.longitude])}
                        style={{ height: '100%', width: '100%' }}
                      >
                        <TileLayer
                          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        />
                        {tourData.sites.map((site, index) => (
                          <Marker
                            key={site.id}
                            position={[site.latitude, site.longitude]}
                            icon={createIcon(index + 1, hoveredSiteId === site.id)}
                          >
                            <Popup>
                              <div>
                                <strong className="font-semibold">
                                  {index + 1}. {site.title}
                                </strong>
                                {site.description && (
                                  <p className="text-xs mt-1 line-clamp-2">
                                    {site.description}
                                  </p>
                                )}
                              </div>
                            </Popup>
                          </Marker>
                        ))}
                      </MapContainer>
                    </div>

                    {/* Sites list */}
                    <div className="space-y-2">
                      {tourData.sites.map((site, index) => (
                        <div
                          key={site.id}
                          className={`flex items-start gap-3 p-3 rounded-lg transition-colors group ${
                            hoveredSiteId === site.id ? 'bg-[#F6EDD9]' : 'hover:bg-[#F6EDD9]/50'
                          }`}
                          onMouseEnter={() => setHoveredSiteId(site.id)}
                          onMouseLeave={() => setHoveredSiteId(null)}
                        >
                          <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-semibold text-sm transition-colors ${
                            hoveredSiteId === site.id ? 'bg-[#8B6F47] text-white' : 'bg-[#F6EDD9] text-[#8B6F47]'
                          }`}>
                            {index + 1}
                          </div>
                          <Link
                            to={`/sites/${site.id}`}
                            state={{
                              fromTour: id,
                              siteIndex: index,
                              totalSites: tourData.sites.length,
                              siteIds: tourData.sites.map(s => s.id)
                            }}
                            className="flex-1 min-w-0"
                          >
                            <div className="font-medium text-gray-900 group-hover:text-[#8B6F47] transition-colors">
                              {site.title}
                            </div>
                            {site.city && site.neighborhood && (
                              <div className="text-sm text-gray-500">
                                {site.neighborhood}, {site.city}
                              </div>
                            )}
                          </Link>
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              setSiteToRemove(site);
                            }}
                            className="flex-shrink-0 w-6 h-6 rounded-full bg-red-100 text-red-600 hover:bg-red-200 hover:text-red-700 flex items-center justify-center transition-colors opacity-0 group-hover:opacity-100"
                            title="Remove site"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>

            </div>
          </form>

          {/* Form Actions - Fixed Bottom */}
          <div className="fixed bottom-0 left-0 right-0 z-10 bg-[#F6EDD9]/95 backdrop-blur-lg border-t border-gray-200/50 pl-64 pr-6 py-4 shadow-lg">
            <div className="flex justify-between items-center">
              {/* Left side - Discard buttons */}
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
                  onClick={handleDiscardAndClose}
                  disabled={saveMutation.isPending}
                  className="px-5 py-2.5 text-sm font-medium text-gray-700 hover:text-gray-900 bg-white hover:bg-gray-50 border border-gray-300 rounded-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Discard & Close
                </button>
              </div>

              {/* Right side - Save buttons */}
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleSaveChanges}
                  disabled={!hasUnsavedChanges || saveMutation.isPending || (!isAdmin && formData.status === 'ready')}
                  className="px-5 py-2.5 bg-white hover:bg-gray-50 text-[#8B6F47] border-2 border-[#8B6F47] text-sm font-semibold rounded-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {saveMutation.isPending ? (
                    <span className="flex items-center gap-2">
                      <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-[#8B6F47]"></div>
                      Saving...
                    </span>
                  ) : (
                    'Save Changes'
                  )}
                </button>
                <button
                  type="button"
                  onClick={handleSaveAndClose}
                  disabled={!hasUnsavedChanges || saveMutation.isPending || (!isAdmin && formData.status === 'ready')}
                  className="px-5 py-2.5 bg-[#8B6F47] hover:bg-[#6F5838] text-white text-sm font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {saveMutation.isPending ? (
                    <span className="flex items-center gap-2">
                      <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Saving...
                    </span>
                  ) : (
                    'Save & Close'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Information Sidebar - Right Column */}
        <div className="lg:col-span-1">
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 p-6 space-y-6 sticky top-20">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-2xl">ℹ️</span>
              Information
            </h2>

            <div className="space-y-4">
              {/* Status */}
              {!isNew && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                    Status
                  </label>
                  <select
                    value={formData.status}
                    onChange={(e) => updateField('status', e.target.value)}
                    disabled={(!isAdmin && formData.status === 'ready') || (!validation.isValid && formData.status === 'draft')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <option value="draft">✏️ Draft</option>
                    <option value="ready" disabled={!isAdmin && !validation.isValid}>🔍 Ready for Review</option>
                    {isAdmin && <option value="published">✅ Published</option>}
                    <option value="archived">📦 Archived</option>
                  </select>
                  <div className="text-xs text-gray-500 mt-1">
                    {formData.status === 'draft' && 'Work in progress'}
                    {formData.status === 'ready' && 'Submitted for review'}
                    {formData.status === 'published' && 'Visible to all users'}
                    {formData.status === 'archived' && 'No longer active'}
                  </div>
                  {!isAdmin && formData.status === 'ready' && (
                    <div className="text-xs text-amber-600 mt-2 flex items-start gap-1">
                      <span>⚠️</span>
                      <span>This tour is under review and cannot be edited until published or returned to draft by an admin.</span>
                    </div>
                  )}
                  {!isAdmin && !validation.isValid && formData.status === 'draft' && (
                    <div className="text-xs text-red-600 mt-2 flex items-start gap-1">
                      <span>⚠️</span>
                      <span>Cannot submit for review until all validation issues are resolved.</span>
                    </div>
                  )}
                </div>
              )}

              {/* Duration */}
              {tourData?.durationMinutes && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
                    Duration
                  </label>
                  <div className="text-sm text-gray-900">
                    {tourData.durationMinutes} minutes
                  </div>
                </div>
              )}

              {/* Distance */}
              {tourData?.distanceMeters && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
                    Distance
                  </label>
                  <div className="text-sm text-gray-900">
                    {(tourData.distanceMeters / 1000).toFixed(2)} km
                  </div>
                </div>
              )}

              {/* Ratings */}
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
                  Rating
                </label>
                {tourData?.ratingCount && tourData.ratingCount >= 25 ? (
                  <div>
                    <div className="text-lg font-semibold text-gray-900">
                      ⭐ {tourData.averageRating?.toFixed(1)}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Based on {tourData.ratingCount} user reviews
                    </div>
                  </div>
                ) : tourData?.calculatedRating ? (
                  <div>
                    <div className="text-lg font-semibold text-gray-900">
                      ⭐ {tourData.calculatedRating.toFixed(1)}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Based on site ratings
                      {tourData.ratingCount > 0 && ` (${tourData.ratingCount} user reviews so far)`}
                    </div>
                  </div>
                ) : (
                  <div className="text-lg text-gray-500">No ratings yet</div>
                )}

                {/* View Feedback button (admin only) */}
                {isAdmin && tourData?.ratingCount > 0 && (
                  <Link
                    to={`/tour-ratings?tourId=${id}`}
                    className="mt-2 inline-flex items-center px-3 py-1 text-sm font-medium text-[#8B6F47] bg-[#F6EDD9] hover:bg-[#8B6F47] hover:text-white rounded-lg transition-colors"
                  >
                    View Feedback →
                  </Link>
                )}
              </div>

              {/* Validation Status */}
              {!isNew && tourData && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                    Validation Status
                  </label>
                  <button
                    onClick={() => setShowValidationReport(true)}
                    className={`w-full px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                      validation.isValid
                        ? 'bg-green-50 text-green-700 hover:bg-green-100 border border-green-200'
                        : 'bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200'
                    }`}
                  >
                    {validation.isValid ? (
                      <span className="flex items-center justify-center gap-2">
                        <span className="text-lg">✓</span>
                        Fully Populated
                      </span>
                    ) : (
                      <span className="flex items-center justify-center gap-2">
                        <span className="text-lg">⚠</span>
                        Incomplete ({validation.issueCount} issue{validation.issueCount !== 1 ? 's' : ''})
                      </span>
                    )}
                  </button>
                  <div className="text-xs text-gray-500 mt-2">
                    Click to view detailed validation report
                  </div>
                </div>
              )}

              {/* Owner */}
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
                  Owner
                </label>
                <div className="text-sm text-gray-900">
                  {isNew ? user?.name : (tourData?.ownerName || `User #${tourData?.ownerId || 'Unknown'}`)}
                </div>
              </div>

              {/* Timestamps */}
              {tourData && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
                      Created
                    </label>
                    <div className="text-sm text-gray-900">
                      {new Date(tourData.createdAt).toLocaleDateString('en-US', {
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
                      {new Date(tourData.updatedAt).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </div>
                  </div>

                  {tourData.publishedAt && (
                    <div>
                      <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
                        Published
                      </label>
                      <div className="text-sm text-gray-900">
                        {new Date(tourData.publishedAt).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Add Site Wizard */}
      <AddSiteWizard
        isOpen={showAddSiteWizard}
        onClose={() => setShowAddSiteWizard(false)}
        onSiteCreated={handleSiteCreated}
        tourId={id}
        initialLocation={
          tourData?.sites && tourData.sites.length > 0
            ? { latitude: tourData.sites[0].latitude, longitude: tourData.sites[0].longitude }
            : tourData?.latitude && tourData?.longitude
            ? { latitude: tourData.latitude, longitude: tourData.longitude }
            : undefined
        }
      />

      {/* Remove Site Dialog */}
      {siteToRemove && (
        <RemoveSiteDialog
          isOpen={!!siteToRemove}
          onClose={() => setSiteToRemove(null)}
          site={siteToRemove}
          tourId={id}
          onRemoveFromTour={handleRemoveFromTour}
          onDeleteSite={handleDeleteSite}
        />
      )}

      {/* Validation Report Modal */}
      <ValidationReportModal
        isOpen={showValidationReport}
        onClose={() => setShowValidationReport(false)}
        validation={validation}
        tourId={id}
      />
    </div>
  );
}
