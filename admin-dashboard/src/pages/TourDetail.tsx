import { useState, FormEvent, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { toursApi, adminToursApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import { usePresignedUrl } from '../hooks/usePresignedUrl';
import type { Tour } from '../types';

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
    audioUrl: '',
    mapImageUrl: '',
    musicUrls: [],
    durationMinutes: undefined,
    distanceMeters: undefined,
  });

  const { data: tourData, isLoading } = useQuery({
    queryKey: ['tour', id],
    queryFn: () => toursApi.get(id!),
    enabled: !isNew && !!id,
  });

  useEffect(() => {
    if (tourData) {
      setFormData(tourData);
    }
  }, [tourData]);

  // Presign S3 URLs for display
  const presignedImageUrl = usePresignedUrl(formData.imageUrl);
  const presignedMapImageUrl = usePresignedUrl(formData.mapImageUrl);

  const saveMutation = useMutation({
    mutationFn: (data: Partial<Tour>) =>
      isNew ? toursApi.create(data) : toursApi.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tours'] });
      toast.success(isNew ? 'Tour created!' : 'Tour updated!');
      navigate('/tours');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to save tour');
    },
  });

  const publishMutation = useMutation({
    mutationFn: (published: boolean) => adminToursApi.publish(id!, published),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tour', id] });
      toast.success('Tour updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to update tour');
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!formData.name) {
      toast.error('Tour name is required');
      return;
    }
    saveMutation.mutate(formData);
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-gray-600 font-medium">Loading tour...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            {isNew ? '✨ Create New Tour' : '✏️ Edit Tour'}
          </h1>
          <p className="text-gray-600 mt-1">
            {isNew ? 'Fill in the details to create a new tour' : 'Update tour information'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => navigate('/tours')}
          className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-lg transition-all"
        >
          ← Back
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content - Left Column */}
        <div className="lg:col-span-2">
          <form id="tour-form" onSubmit={handleSubmit} className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 overflow-hidden">
            <div className="p-8 pb-32 space-y-8">
              {/* Basic Information Section */}
              <div className="space-y-4">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <span className="text-2xl">📝</span>
                  Basic Information
                </h2>

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
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white"
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
                    placeholder="Describe the tour..."
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white resize-none"
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
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white"
                  />
                  {presignedImageUrl && (
                    <img src={presignedImageUrl} alt="Tour" className="mt-2 h-32 rounded-lg object-cover" />
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
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white"
                  />
                  {formData.audioUrl && (
                    <audio controls className="mt-2 w-full">
                      <source src={formData.audioUrl} />
                    </audio>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Map Image URL
                  </label>
                  <input
                    type="url"
                    value={formData.mapImageUrl || ''}
                    onChange={(e) => updateField('mapImageUrl', e.target.value)}
                    placeholder="https://s3.amazonaws.com/..."
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white"
                  />
                  {presignedMapImageUrl && (
                    <img src={presignedMapImageUrl} alt="Map" className="mt-2 h-32 rounded-lg object-cover" />
                  )}
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Background Music URLs
                    </label>
                    <button
                      type="button"
                      onClick={addMusicUrl}
                      className="text-sm text-blue-600 hover:text-blue-700"
                    >
                      + Add Music
                    </button>
                  </div>
                  <div className="space-y-2">
                    {(formData.musicUrls || []).map((url, index) => (
                      <div key={index} className="flex gap-2">
                        <input
                          type="url"
                          value={url}
                          onChange={(e) => updateMusicUrl(index, e.target.value)}
                          placeholder="https://s3.amazonaws.com/..."
                          className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white"
                        />
                        <button
                          type="button"
                          onClick={() => removeMusicUrl(index)}
                          className="px-3 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Metadata Section */}
              <div className="space-y-4 pt-6 border-t border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <span className="text-2xl">📊</span>
                  Metadata
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Duration (minutes)
                    </label>
                    <input
                      type="number"
                      value={formData.durationMinutes || ''}
                      onChange={(e) => updateField('durationMinutes', parseInt(e.target.value) || null)}
                      placeholder="60"
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Distance (meters)
                    </label>
                    <input
                      type="number"
                      value={formData.distanceMeters || ''}
                      onChange={(e) => updateField('distanceMeters', parseFloat(e.target.value) || null)}
                      placeholder="1500"
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white"
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
                        <Link
                          key={site.id}
                          to={`/sites/${site.id}`}
                          className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors group"
                        >
                          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-semibold text-sm">
                            {index + 1}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-gray-900 group-hover:text-blue-600 transition-colors">
                              {site.title}
                            </div>
                            {site.city && site.neighborhood && (
                              <div className="text-sm text-gray-500">
                                {site.neighborhood}, {site.city}
                              </div>
                            )}
                          </div>
                          <div className="flex-shrink-0 text-gray-400 group-hover:text-blue-600">
                            →
                          </div>
                        </Link>
                      ))}
                    </div>
                  </>
                )}
              </div>

            </div>
          </form>

          {/* Form Actions - Fixed Bottom */}
          <div className="fixed bottom-0 left-0 right-0 z-10 bg-white border-t border-gray-200 pl-64 pr-6 py-4 flex justify-end gap-3">
            <button
              type="button"
              onClick={() => navigate('/tours')}
              className="px-6 py-3 text-sm font-medium text-gray-700 hover:text-gray-900 bg-white hover:bg-gray-50 border border-gray-300 rounded-xl transition-all duration-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              form="tour-form"
              disabled={saveMutation.isPending}
              className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white text-sm font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
            >
              {saveMutation.isPending ? (
                <span className="flex items-center gap-2">
                  <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Saving...
                </span>
              ) : (
                <span>{isNew ? '✨ Create Tour' : '💾 Save Changes'}</span>
              )}
            </button>
          </div>
        </div>

        {/* Information Sidebar - Right Column */}
        <div className="lg:col-span-1">
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 p-6 space-y-6 sticky top-6">
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
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white text-sm"
                  >
                    <option value="draft">✏️ Draft</option>
                    <option value="live">✅ Live</option>
                    <option value="archived">📦 Archived</option>
                  </select>
                  <div className="text-xs text-gray-500 mt-1">
                    {formData.status === 'draft' && 'Work in progress'}
                    {formData.status === 'live' && 'Active and ready'}
                    {formData.status === 'archived' && 'No longer active'}
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
              </div>

              {/* Published Status */}
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                  Published
                </label>
                {isAdmin && !isNew ? (
                  <>
                    <button
                      type="button"
                      onClick={() => publishMutation.mutate(!tourData?.isPublic)}
                      disabled={publishMutation.isPending || formData.status !== 'live'}
                      className={`relative inline-flex h-8 w-16 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${
                        tourData?.isPublic ? 'bg-green-500' : 'bg-gray-300'
                      }`}
                    >
                      <span
                        className={`inline-block h-6 w-6 transform rounded-full bg-white shadow-lg transition-transform ${
                          tourData?.isPublic ? 'translate-x-9' : 'translate-x-1'
                        }`}
                      />
                      <span className="sr-only">Toggle public status</span>
                    </button>
                    <div className="text-xs text-gray-500 mt-1">
                      {formData.status !== 'live' ? (
                        <span className="text-amber-600">Tour must be &apos;live&apos; to be published</span>
                      ) : tourData?.isPublic ? (
                        'Visible to everyone'
                      ) : (
                        'Only visible to owner and admins'
                      )}
                    </div>
                  </>
                ) : (
                  <>
                    <span
                      className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${
                        tourData?.isPublic
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {tourData?.isPublic ? '🌐 Public' : '🔒 Private'}
                    </span>
                    <div className="text-xs text-gray-500 mt-1">
                      {tourData?.isPublic ? 'Visible to everyone' : 'Only visible to owner and admins'}
                    </div>
                  </>
                )}
              </div>

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
    </div>
  );
}
