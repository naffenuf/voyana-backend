import { useState, FormEvent, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { useAuth } from '../lib/auth';
import { sitesApi } from '../lib/api';
import { usePresignedUrl, usePresignedUrls } from '../hooks/usePresignedUrl';
import type { Site } from '../types';

export default function SiteDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAdmin } = useAuth();
  const isNew = id === 'new';

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

  const [keywordInput, setKeywordInput] = useState('');
  const [typeInput, setTypeInput] = useState('');

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
        navigate('/sites');
      }
    } else {
      navigate('/sites');
    }
  };

  const updateField = (field: keyof Site, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const addKeyword = () => {
    if (keywordInput.trim()) {
      const keywords = formData.keywords || [];
      setFormData((prev) => ({ ...prev, keywords: [...keywords, keywordInput.trim()] }));
      setKeywordInput('');
    }
  };

  const removeKeyword = (index: number) => {
    const keywords = [...(formData.keywords || [])];
    keywords.splice(index, 1);
    setFormData((prev) => ({ ...prev, keywords }));
  };

  const addType = () => {
    if (typeInput.trim()) {
      const types = formData.types || [];
      setFormData((prev) => ({ ...prev, types: [...types, typeInput.trim()] }));
      setTypeInput('');
    }
  };

  const removeType = (index: number) => {
    const types = [...(formData.types || [])];
    types.splice(index, 1);
    setFormData((prev) => ({ ...prev, types }));
  };

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
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {isNew ? 'Create New Site' : 'Edit Site'}
            </h1>
            <p className="text-gray-600 mt-1">
              {isNew
                ? 'Fill in the details to create a new site'
                : 'Update site information'}
            </p>
          </div>
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
          {/* Form */}
          <form id="site-form" onSubmit={handleSubmit} className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 overflow-hidden">
            <div className="p-8 pb-32 space-y-8">
          {/* Basic Information Section */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-2xl">📝</span>
              Basic Information
            </h2>

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

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                rows={5}
                
                value={formData.description || ''}
                onChange={(e) => updateField('description', e.target.value)}
                placeholder="Describe the site..."
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white resize-none disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            </div>
          </div>

          {/* Media Section */}
          <div className="space-y-4 pt-6 border-t border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-2xl">🎬</span>
              Media
            </h2>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Image URL
              </label>
              <input
                type="url"
                
                value={formData.imageUrl || ''}
                onChange={(e) => updateField('imageUrl', e.target.value)}
                placeholder="https://s3.amazonaws.com/..."
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              {presignedImageUrl && (
                <img src={presignedImageUrl} alt="Site" className="mt-2 h-32 rounded-lg object-cover" />
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Audio URL
              </label>
              <input
                type="url"
                
                value={formData.audioUrl || ''}
                onChange={(e) => updateField('audioUrl', e.target.value)}
                placeholder="https://s3.amazonaws.com/..."
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              {presignedAudioUrl && (
                <audio controls className="mt-2 w-full">
                  <source src={presignedAudioUrl} />
                </audio>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Web URL
              </label>
              <input
                type="url"
                
                value={formData.webUrl || ''}
                onChange={(e) => updateField('webUrl', e.target.value)}
                placeholder="https://example.com"
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            </div>
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
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-2xl">📍</span>
              {formData.neighborhood && formData.city
                ? `${formData.neighborhood}, ${formData.city}`
                : formData.city || formData.neighborhood || 'Location'}
            </h2>

            {/* Map with single site marker */}
            {formData.latitude && formData.longitude && (
              <div className="h-96 rounded-xl overflow-hidden border-2 border-gray-200">
                <MapContainer
                  center={[formData.latitude, formData.longitude]}
                  zoom={15}
                  style={{ height: '100%', width: '100%' }}
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <Marker position={[formData.latitude, formData.longitude]}>
                    <Popup>
                      <div>
                        <strong className="font-semibold">{formData.title}</strong>
                        {formData.description && (
                          <p className="text-xs mt-1 line-clamp-2">{formData.description}</p>
                        )}
                      </div>
                    </Popup>
                  </Marker>
                </MapContainer>
              </div>
            )}
          </div>

          {/* Discovery Section */}
          <div className="space-y-4 pt-6 border-t border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-2xl">🔍</span>
              Discovery
            </h2>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Keywords
              </label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  
                  value={keywordInput}
                  onChange={(e) => setKeywordInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addKeyword())}
                  placeholder="Add keyword and press Enter..."
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
                
                  <button
                    type="button"
                    onClick={addKeyword}
                    className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
                  >
                    Add
                  </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {(formData.keywords || []).map((keyword, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
                  >
                    {keyword}
                    
                      <button
                        type="button"
                        onClick={() => removeKeyword(index)}
                        className="text-gray-500 hover:text-red-600"
                      >
                        ✕
                      </button>
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Google Places Section */}
          <div className="space-y-4 pt-6 border-t border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-2xl">🗺️</span>
              Google Places
            </h2>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Place ID
              </label>
              <input
                type="text"
                disabled
                value={formData.placeId || ''}
                className="w-full px-4 py-3 border border-gray-200 rounded-xl bg-gray-50 text-gray-600"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Formatted Address
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
                Types
              </label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  
                  value={typeInput}
                  onChange={(e) => setTypeInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addType())}
                  placeholder="Add type and press Enter..."
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
                
                  <button
                    type="button"
                    onClick={addType}
                    className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
                  >
                    Add
                  </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {(formData.types || []).map((type, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm"
                  >
                    {type}
                    
                      <button
                        type="button"
                        onClick={() => removeType(index)}
                        className="text-blue-500 hover:text-red-600"
                      >
                        ✕
                      </button>
                  </span>
                ))}
              </div>
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
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 p-6 space-y-6 sticky top-6">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-2xl">ℹ️</span>
              Information
            </h2>

            <div className="space-y-4">
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
              disabled={!hasUnsavedChanges || saveMutation.isPending}
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
              disabled={!hasUnsavedChanges || saveMutation.isPending}
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
  );
}
