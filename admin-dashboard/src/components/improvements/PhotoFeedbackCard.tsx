import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { Camera, MapPin, Check, X, User, Calendar, FileText, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminPhotoSubmissionsApi, sitesApi, mediaApi } from '../../lib/api';
import type { Feedback } from '../../types';

// Fix for default marker icons in react-leaflet
import 'leaflet/dist/leaflet.css';
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface PhotoFeedbackCardProps {
  feedback: Feedback;
  onDelete: () => void;
}

export default function PhotoFeedbackCard({ feedback, onDelete }: PhotoFeedbackCardProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [adminNotes, setAdminNotes] = useState(feedback.adminNotes || '');
  const [isEditingNotes, setIsEditingNotes] = useState(false);
  const [expandedImage, setExpandedImage] = useState<string | null>(null);
  const [currentSiteImage, setCurrentSiteImage] = useState<string | null>(null);

  // Fetch site details to get current image
  const [siteLoading, setSiteLoading] = useState(false);

  // Process photo data URL - clean Base64 data
  const photoDataUrl = feedback.photoData
    ? (() => {
        if (feedback.photoData.startsWith('data:')) {
          return feedback.photoData;
        }
        // Clean the Base64 string - remove whitespace, newlines, etc.
        const cleanBase64 = feedback.photoData.replace(/\s/g, '');

        // Validate it looks like Base64 (only valid Base64 characters)
        if (!/^[A-Za-z0-9+/=]+$/.test(cleanBase64)) {
          console.error('Invalid Base64 characters detected');
          return null;
        }

        return `data:image/jpeg;base64,${cleanBase64}`;
      })()
    : null;

  // Debug logging
  console.log('PhotoFeedbackCard feedback:', {
    id: feedback.id,
    hasPhotoData: !!feedback.photoData,
    photoDataLength: feedback.photoData?.length,
    photoDataPreview: feedback.photoData?.substring(0, 50),
    hasWhitespace: feedback.photoData ? /\s/.test(feedback.photoData) : false,
    cleanedLength: photoDataUrl ? (photoDataUrl.length - 'data:image/jpeg;base64,'.length) : 0,
    photoDataUrl: photoDataUrl?.substring(0, 100),
    photoDetail: feedback.photoDetail,
  });

  // Load site image on mount
  useEffect(() => {
    if (feedback.siteId) {
      setSiteLoading(true);
      sitesApi.get(feedback.siteId)
        .then(async (site) => {
          console.log('Loaded site:', site);
          if (site.imageUrl) {
            console.log('Site imageUrl:', site.imageUrl);
            try {
              const presignedUrl = await mediaApi.getPresignedUrl(site.imageUrl);
              console.log('Presigned URL:', presignedUrl);
              setCurrentSiteImage(presignedUrl);
            } catch (err) {
              console.error('Failed to get presigned URL:', err);
              // Try using the original URL as fallback
              setCurrentSiteImage(site.imageUrl);
            }
          } else {
            console.log('No imageUrl on site');
          }
        })
        .catch((err) => {
          console.error('Failed to load site:', err);
        })
        .finally(() => {
          setSiteLoading(false);
        });
    }
  }, [feedback.siteId]);

  // Update mutation (status and notes)
  const updateMutation = useMutation({
    mutationFn: (data: { status?: string; adminNotes?: string }) =>
      adminPhotoSubmissionsApi.update(feedback.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['photo-submissions'] });
      toast.success('Photo submission updated');
      setIsEditingNotes(false);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to update');
    },
  });

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: (options: { replaceImage: boolean; updateLocation: boolean }) =>
      adminPhotoSubmissionsApi.approve(feedback.id, options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['photo-submissions'] });
      queryClient.invalidateQueries({ queryKey: ['sites-list'] });
      toast.success('Photo approved and processed');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to approve photo');
    },
  });

  const handleStatusChange = (newStatus: string) => {
    updateMutation.mutate({ status: newStatus });
  };

  const handleSaveNotes = () => {
    updateMutation.mutate({ adminNotes });
  };

  const handleApprove = (replaceImage: boolean, updateLocation: boolean) => {
    if (window.confirm(`Are you sure you want to approve this photo${replaceImage ? ' and replace the site image' : ''}${updateLocation ? ' and update the location' : ''}?`)) {
      approveMutation.mutate({ replaceImage, updateLocation });
    }
  };

  const photoDetail = feedback.photoDetail;
  const site = feedback.site;

  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-800',
    reviewed: 'bg-blue-100 text-blue-800',
    resolved: 'bg-green-100 text-green-800',
    dismissed: 'bg-gray-100 text-gray-800',
  };

  return (
    <>
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Camera className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-gray-900">Photo Submission</h3>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[feedback.status as keyof typeof statusColors]}`}>
                  {feedback.status}
                </span>
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
                <div className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  {new Date(feedback.createdAt).toLocaleDateString()}
                </div>
                {feedback.user && (
                  <div className="flex items-center gap-1">
                    <User className="w-4 h-4" />
                    {feedback.user.name || feedback.user.email}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Status dropdown and delete */}
          <div className="flex items-center gap-2">
            <select
              value={feedback.status}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-[#8B6F47] focus:border-[#8B6F47]"
              disabled={updateMutation.isPending}
            >
              <option value="pending">Pending</option>
              <option value="reviewed">Reviewed</option>
              <option value="resolved">Resolved</option>
              <option value="dismissed">Dismissed</option>
            </select>

            <button
              onClick={onDelete}
              className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              title="Delete"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Site and Tour info */}
        {(site || feedback.tour) && (
          <div className="flex items-center gap-4 mb-4 text-sm">
            {site && (
              <button
                onClick={() => navigate(`/sites/${feedback.siteId}`)}
                className="flex items-center gap-1 text-[#8B6F47] hover:underline"
              >
                <MapPin className="w-4 h-4" />
                {site.title}
              </button>
            )}
            {feedback.tour && (
              <button
                onClick={() => navigate(`/tours/${feedback.tourId}`)}
                className="text-gray-600 hover:underline"
              >
                {feedback.tour.name}
              </button>
            )}
          </div>
        )}

        {/* Caption */}
        {photoDetail?.caption && (
          <div className="mb-4">
            <p className="text-gray-700">{photoDetail.caption}</p>
          </div>
        )}

        {/* Photos Row */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          {/* Submitted Photo */}
          <div className="space-y-2">
            <div className="text-sm font-medium text-gray-700">Submitted Photo</div>
            <div className="relative w-full" style={{ paddingBottom: '75%' }}>
              {photoDataUrl ? (
                <div
                  className="absolute inset-0 rounded-lg overflow-hidden cursor-pointer bg-gray-100"
                  onClick={() => setExpandedImage(photoDataUrl)}
                  style={{
                    backgroundImage: `url("${photoDataUrl}")`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    backgroundRepeat: 'no-repeat'
                  }}
                />
              ) : (
                <div className="absolute inset-0 bg-gray-100 rounded-lg flex items-center justify-center text-gray-400">
                  No image
                </div>
              )}
            </div>
          </div>

          {/* Current Site Photo */}
          <div className="space-y-2">
            <div className="text-sm font-medium text-gray-700">Current Site Photo</div>
            <div className="relative w-full" style={{ paddingBottom: '75%' }}>
              {siteLoading ? (
                <div className="absolute inset-0 bg-gray-100 rounded-lg flex items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#8B6F47]"></div>
                </div>
              ) : currentSiteImage ? (
                <div
                  className="absolute inset-0 rounded-lg overflow-hidden cursor-pointer bg-gray-100"
                  onClick={() => setExpandedImage(currentSiteImage)}
                  style={{
                    backgroundImage: `url("${currentSiteImage}")`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    backgroundRepeat: 'no-repeat'
                  }}
                />
              ) : (
                <div className="absolute inset-0 bg-gray-100 rounded-lg flex items-center justify-center text-gray-400 text-sm">
                  No current photo
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Maps Row */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          {/* Site Location Map */}
          {site && site.latitude !== undefined && site.longitude !== undefined && (
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-700">Current Site Location</div>
              <div className="aspect-square rounded-lg overflow-hidden border border-gray-200 relative z-0">
                <MapContainer
                  center={[site.latitude, site.longitude]}
                  zoom={16}
                  style={{ height: '100%', width: '100%', zIndex: 0 }}
                  zoomControl={false}
                  dragging={false}
                  scrollWheelZoom={false}
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <Marker position={[site.latitude, site.longitude]}>
                    <Popup>Current Site Location</Popup>
                  </Marker>
                </MapContainer>
              </div>
              <div className="text-xs text-gray-500 text-center">
                {site.latitude.toFixed(6)}, {site.longitude.toFixed(6)}
              </div>
            </div>
          )}

          {/* Photo Location Map */}
          {photoDetail?.latitude && photoDetail?.longitude && (
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-700">Camera Location</div>
              <div className="aspect-square rounded-lg overflow-hidden border border-gray-200 relative z-0">
                <MapContainer
                  center={[photoDetail.latitude, photoDetail.longitude]}
                  zoom={16}
                  style={{ height: '100%', width: '100%', zIndex: 0 }}
                  zoomControl={false}
                  dragging={false}
                  scrollWheelZoom={false}
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <Marker position={[photoDetail.latitude, photoDetail.longitude]}>
                    <Popup>Camera Location</Popup>
                  </Marker>
                </MapContainer>
              </div>
              <div className="text-xs text-gray-500 text-center">
                {photoDetail.latitude.toFixed(6)}, {photoDetail.longitude.toFixed(6)}
              </div>
            </div>
          )}
        </div>

        {/* Approval Actions */}
        {feedback.status === 'pending' && (
          <div className="mb-4 p-4 bg-blue-50 rounded-lg">
            <div className="text-sm font-medium text-gray-700 mb-3">Approval Actions</div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => handleApprove(true, false)}
                disabled={approveMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-[#8B6F47] text-white rounded-lg hover:bg-[#6B5437] font-medium transition-colors disabled:opacity-50"
              >
                <Check className="w-4 h-4" />
                Replace Photo Only
              </button>

              {photoDetail?.latitude && photoDetail?.longitude && (
                <>
                  <button
                    onClick={() => handleApprove(false, true)}
                    disabled={approveMutation.isPending}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium transition-colors disabled:opacity-50"
                  >
                    <Check className="w-4 h-4" />
                    Replace Location Only
                  </button>

                  <button
                    onClick={() => handleApprove(true, true)}
                    disabled={approveMutation.isPending}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium transition-colors disabled:opacity-50"
                  >
                    <Check className="w-4 h-4" />
                    Replace Photo & Location
                  </button>
                </>
              )}

              <button
                onClick={() => handleApprove(false, false)}
                disabled={approveMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors disabled:opacity-50"
              >
                <Check className="w-4 h-4" />
                Save to S3 Only
              </button>
            </div>
          </div>
        )}

        {/* Admin Notes */}
        <div className="border-t border-gray-200 pt-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <FileText className="w-4 h-4" />
              Admin Notes
            </div>
            {!isEditingNotes && (
              <button
                onClick={() => setIsEditingNotes(true)}
                className="text-sm text-[#8B6F47] hover:underline"
              >
                Edit
              </button>
            )}
          </div>

          {isEditingNotes ? (
            <div className="space-y-2">
              <textarea
                value={adminNotes}
                onChange={(e) => setAdminNotes(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-[#8B6F47]"
                rows={3}
                placeholder="Add admin notes..."
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSaveNotes}
                  disabled={updateMutation.isPending}
                  className="px-4 py-2 bg-[#8B6F47] text-white rounded-lg hover:bg-[#6B5437] font-medium transition-colors disabled:opacity-50"
                >
                  Save
                </button>
                <button
                  onClick={() => {
                    setAdminNotes(feedback.adminNotes || '');
                    setIsEditingNotes(false);
                  }}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-600">
              {adminNotes || <span className="text-gray-400 italic">No notes yet</span>}
            </div>
          )}

          {feedback.reviewedBy && feedback.reviewer && (
            <div className="mt-3 text-xs text-gray-500">
              Reviewed by {feedback.reviewer.name || feedback.reviewer.email} on{' '}
              {feedback.reviewedAt && new Date(feedback.reviewedAt).toLocaleString()}
            </div>
          )}
        </div>
      </div>

      {/* Expanded Image Modal */}
      {expandedImage && (
        <div
          className="fixed inset-0 z-50 bg-black bg-opacity-90 flex items-center justify-center p-4"
          onClick={() => setExpandedImage(null)}
        >
          <div className="relative max-w-6xl max-h-full">
            <button
              onClick={() => setExpandedImage(null)}
              className="absolute top-4 right-4 p-2 bg-white rounded-full hover:bg-gray-100 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
            <img
              src={expandedImage}
              alt="Expanded view"
              className="max-w-full max-h-[90vh] object-contain"
            />
          </div>
        </div>
      )}
    </>
  );
}
