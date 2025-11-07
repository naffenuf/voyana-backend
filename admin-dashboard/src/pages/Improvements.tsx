import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminPhotoSubmissionsApi, adminLocationDataApi, adminFeedbackApi, toursApi, sitesApi } from '../lib/api';
import { Filter, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import type { Feedback } from '../types';
import PhotoFeedbackCard from '../components/improvements/PhotoFeedbackCard';
import LocationFeedbackCard from '../components/improvements/LocationFeedbackCard';
import CommentFeedbackCard from '../components/improvements/CommentFeedbackCard';

export default function Improvements() {
  const queryClient = useQueryClient();

  // Filter states
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [siteFilter, setSiteFilter] = useState<string>('');
  const [tourFilter, setTourFilter] = useState<string>('');

  // Fetch photo submissions
  const { data: photosData, isLoading: photosLoading } = useQuery({
    queryKey: ['photo-submissions', statusFilter, siteFilter, tourFilter],
    queryFn: () =>
      adminPhotoSubmissionsApi.list({
        status: statusFilter || undefined,
        site_id: siteFilter || undefined,
        tour_id: tourFilter || undefined,
        limit: 500,
      }),
    enabled: !typeFilter || typeFilter === 'photo',
  });

  // Fetch location submissions
  const { data: locationsData, isLoading: locationsLoading } = useQuery({
    queryKey: ['location-submissions', statusFilter, siteFilter, tourFilter],
    queryFn: () =>
      adminLocationDataApi.list({
        status: statusFilter || undefined,
        site_id: siteFilter || undefined,
        tour_id: tourFilter || undefined,
        limit: 500,
      }),
    enabled: !typeFilter || typeFilter === 'location',
  });

  // Fetch comment feedback
  const { data: commentsData, isLoading: commentsLoading } = useQuery({
    queryKey: ['comment-feedback', statusFilter, siteFilter, tourFilter],
    queryFn: () =>
      adminFeedbackApi.list({
        feedback_type: 'comment',
        status: statusFilter || undefined,
        site_id: siteFilter || undefined,
        tour_id: tourFilter || undefined,
        limit: 500,
      }),
    enabled: !typeFilter || typeFilter === 'comment',
  });

  // Fetch tours for filter dropdown
  const { data: toursData } = useQuery({
    queryKey: ['tours-list'],
    queryFn: () => toursApi.list({ limit: 10000 }),
  });

  // Fetch sites for filter dropdown
  const { data: sitesData } = useQuery({
    queryKey: ['sites-list'],
    queryFn: () => sitesApi.list({ limit: 10000 }),
  });

  // Combine all improvements into a single list
  const allImprovements = useMemo(() => {
    const photos = (!typeFilter || typeFilter === 'photo') ? (photosData?.photos || []) : [];
    const locations = (!typeFilter || typeFilter === 'location') ? (locationsData?.locations || []) : [];
    const comments = (!typeFilter || typeFilter === 'comment') ? (commentsData?.feedback || []) : [];

    const combined = [...photos, ...locations, ...comments];

    // Sort by created date, most recent first
    return combined.sort((a, b) => {
      const dateA = new Date(a.createdAt).getTime();
      const dateB = new Date(b.createdAt).getTime();
      return dateB - dateA;
    });
  }, [photosData, locationsData, commentsData, typeFilter]);

  const isLoading = photosLoading || locationsLoading || commentsLoading;

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async ({ id, type }: { id: number; type: string }) => {
      if (type === 'photo') {
        await adminPhotoSubmissionsApi.delete(id);
      } else if (type === 'location') {
        await adminLocationDataApi.delete(id);
      } else {
        await adminFeedbackApi.delete(id);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['photo-submissions'] });
      queryClient.invalidateQueries({ queryKey: ['location-submissions'] });
      queryClient.invalidateQueries({ queryKey: ['comment-feedback'] });
      toast.success('Improvement deleted successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to delete improvement');
    },
  });

  const handleClearFilters = () => {
    setTypeFilter('');
    setStatusFilter('pending');
    setSiteFilter('');
    setTourFilter('');
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Improvements</h1>
          <p className="text-gray-600 mt-1">
            Review and manage user-submitted photos, location corrections, and comments
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-5 h-5 text-gray-600" />
          <h2 className="font-semibold text-gray-900">Filters</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Type filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type
            </label>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-[#8B6F47]"
            >
              <option value="">All Types</option>
              <option value="photo">Photo Submissions</option>
              <option value="location">Location Corrections</option>
              <option value="comment">Comments</option>
            </select>
          </div>

          {/* Status filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-[#8B6F47]"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="reviewed">Reviewed</option>
              <option value="resolved">Resolved</option>
              <option value="dismissed">Dismissed</option>
            </select>
          </div>

          {/* Tour filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tour
            </label>
            <select
              value={tourFilter}
              onChange={(e) => setTourFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-[#8B6F47]"
            >
              <option value="">All Tours</option>
              {toursData?.tours?.map((tour) => (
                <option key={tour.id} value={tour.id}>
                  {tour.name}
                </option>
              ))}
            </select>
          </div>

          {/* Site filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Site
            </label>
            <select
              value={siteFilter}
              onChange={(e) => setSiteFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-[#8B6F47]"
            >
              <option value="">All Sites</option>
              {sitesData?.sites?.map((site) => (
                <option key={site.id} value={site.id}>
                  {site.title}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={handleClearFilters}
          className="mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 font-medium transition-colors"
        >
          Clear Filters
        </button>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#8B6F47]"></div>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && allImprovements.length === 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No improvements found</h3>
          <p className="text-gray-600">
            No improvements match your current filters. Try adjusting the filters above.
          </p>
        </div>
      )}

      {/* Improvements list */}
      {!isLoading && allImprovements.length > 0 && (
        <div className="space-y-4">
          <div className="text-sm text-gray-600 mb-4">
            Showing {allImprovements.length} improvement{allImprovements.length !== 1 ? 's' : ''}
          </div>

          {allImprovements.map((improvement) => {
            if (improvement.feedbackType === 'photo') {
              return (
                <PhotoFeedbackCard
                  key={`photo-${improvement.id}`}
                  feedback={improvement}
                  onDelete={() => deleteMutation.mutate({ id: improvement.id, type: 'photo' })}
                />
              );
            } else if (improvement.feedbackType === 'location') {
              return (
                <LocationFeedbackCard
                  key={`location-${improvement.id}`}
                  feedback={improvement}
                  onDelete={() => deleteMutation.mutate({ id: improvement.id, type: 'location' })}
                />
              );
            } else if (improvement.feedbackType === 'comment') {
              return (
                <CommentFeedbackCard
                  key={`comment-${improvement.id}`}
                  feedback={improvement}
                  onDelete={() => deleteMutation.mutate({ id: improvement.id, type: 'comment' })}
                />
              );
            }
            return null;
          })}
        </div>
      )}
    </div>
  );
}
