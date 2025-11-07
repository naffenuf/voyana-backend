import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { MapPin, Check, User, Calendar, FileText, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminLocationDataApi } from '../../lib/api';
import type { Feedback } from '../../types';

// Fix for default marker icons
import 'leaflet/dist/leaflet.css';
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface LocationFeedbackCardProps {
  feedback: Feedback;
  onDelete: () => void;
}

export default function LocationFeedbackCard({ feedback, onDelete }: LocationFeedbackCardProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [adminNotes, setAdminNotes] = useState(feedback.adminNotes || '');
  const [isEditingNotes, setIsEditingNotes] = useState(false);

  // Update mutation (status and notes)
  const updateMutation = useMutation({
    mutationFn: (data: { status?: string; adminNotes?: string }) =>
      adminLocationDataApi.update(feedback.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['location-submissions'] });
      toast.success('Location submission updated');
      setIsEditingNotes(false);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to update');
    },
  });

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: () => adminLocationDataApi.approve(feedback.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['location-submissions'] });
      queryClient.invalidateQueries({ queryKey: ['sites-list'] });
      toast.success('Location approved and added to site');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to approve location');
    },
  });

  const handleStatusChange = (newStatus: string) => {
    updateMutation.mutate({ status: newStatus });
  };

  const handleSaveNotes = () => {
    updateMutation.mutate({ adminNotes });
  };

  const handleApprove = () => {
    if (window.confirm('Are you sure you want to approve this location correction?')) {
      approveMutation.mutate();
    }
  };

  const locationDetail = feedback.locationDetail;
  const site = feedback.site;

  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-800',
    reviewed: 'bg-blue-100 text-blue-800',
    resolved: 'bg-green-100 text-green-800',
    dismissed: 'bg-gray-100 text-gray-800',
  };

  // Calculate distance between two points in meters
  const calculateDistance = (lat1: number, lon1: number, lat2: number, lon2: number) => {
    const R = 6371e3; // Earth radius in meters
    const φ1 = lat1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const Δφ = (lat2 - lat1) * Math.PI / 180;
    const Δλ = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c;
  };

  const distance = site && locationDetail
    ? calculateDistance(site.latitude, site.longitude, locationDetail.latitude, locationDetail.longitude)
    : null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <MapPin className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-900">Location Correction</h3>
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

      {/* Distance info */}
      {distance !== null && (
        <div className="mb-4 p-3 bg-blue-50 rounded-lg">
          <div className="text-sm font-medium text-gray-900">
            Distance from current location: <span className="text-blue-600">{distance.toFixed(1)}m</span>
          </div>
          {locationDetail?.accuracy && (
            <div className="text-xs text-gray-600 mt-1">
              Reported accuracy: ±{locationDetail.accuracy.toFixed(1)}m
            </div>
          )}
        </div>
      )}

      {/* Maps Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        {/* Current Site Location Map */}
        {site && (
          <div className="space-y-2">
            <div className="text-sm font-medium text-gray-700">
              Current Site Location
              <div className="text-xs text-gray-500 font-normal">
                {site.latitude.toFixed(6)}, {site.longitude.toFixed(6)}
              </div>
            </div>
            <div className="h-64 rounded-lg overflow-hidden border border-gray-200">
              <MapContainer
                center={[site.latitude, site.longitude]}
                zoom={17}
                style={{ height: '100%', width: '100%' }}
                zoomControl={true}
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
          </div>
        )}

        {/* Submitted Location Map */}
        {locationDetail && (
          <div className="space-y-2">
            <div className="text-sm font-medium text-gray-700">
              Submitted Location
              <div className="text-xs text-gray-500 font-normal">
                {locationDetail.latitude.toFixed(6)}, {locationDetail.longitude.toFixed(6)}
              </div>
            </div>
            <div className="h-64 rounded-lg overflow-hidden border border-gray-200">
              <MapContainer
                center={[locationDetail.latitude, locationDetail.longitude]}
                zoom={17}
                style={{ height: '100%', width: '100%' }}
                zoomControl={true}
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <Marker position={[locationDetail.latitude, locationDetail.longitude]}>
                  <Popup>
                    Submitted Location
                    {locationDetail.recordedAt && (
                      <div className="text-xs mt-1">
                        Recorded: {new Date(locationDetail.recordedAt).toLocaleString()}
                      </div>
                    )}
                  </Popup>
                </Marker>
              </MapContainer>
            </div>
          </div>
        )}
      </div>

      {/* User Comment */}
      {feedback.comment && (
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <div className="text-sm font-medium text-gray-700 mb-1">User Comment</div>
          <div className="text-sm text-gray-600">{feedback.comment}</div>
        </div>
      )}

      {/* Approval Action */}
      {feedback.status === 'pending' && (
        <div className="flex items-center gap-2 mb-4 p-3 bg-blue-50 rounded-lg">
          <button
            onClick={handleApprove}
            disabled={approveMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-[#8B6F47] text-white rounded-lg hover:bg-[#6B5437] font-medium transition-colors disabled:opacity-50"
          >
            <Check className="w-4 h-4" />
            Approve & Add to Site Locations
          </button>
          <div className="text-xs text-gray-600">
            This will add the location to the site's user-submitted locations array
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
  );
}
