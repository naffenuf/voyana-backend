import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../lib/auth';
import { toursApi, adminToursApi } from '../lib/api';
import type { Tour } from '../types';

// Helper function to get status display info
function getStatusDisplay(status: string) {
  const statusMap: Record<string, { label: string; className: string }> = {
    draft: { label: 'Draft', className: 'bg-gray-100 text-gray-600' },
    ready: { label: 'Ready for Review', className: 'bg-blue-100 text-blue-700' },
    published: { label: 'Published', className: 'bg-[#944F2E] text-white' },
    archived: { label: 'Archived', className: 'bg-gray-200 text-gray-500' },
  };
  return statusMap[status] || { label: status, className: 'bg-gray-100 text-gray-600' };
}

export default function Tours() {
  const { user, isAdmin } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [cityFilter, setCityFilter] = useState('');

  // Use admin API if user is admin, otherwise regular API
  const { data, isLoading } = useQuery({
    queryKey: ['tours', search, statusFilter, cityFilter, isAdmin],
    queryFn: () => {
      const filters = {
        search: search || undefined,
        status: statusFilter || undefined,
        city: cityFilter || undefined,
        limit: 50,
      };
      return isAdmin ? adminToursApi.list(filters) : toursApi.list(filters);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => toursApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tours'] });
      toast.success('Tour deleted successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to delete tour');
    },
  });

  const handleDelete = (tour: Tour) => {
    if (!confirm(`Are you sure you want to delete "${tour.name}"?`)) return;
    deleteMutation.mutate(tour.id);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Tours</h1>
          <p className="text-gray-600 mt-1">Manage your tour collection</p>
        </div>
        <Link
          to="/tours/new"
          className="px-6 py-2.5 bg-[#944F2E] hover:bg-[#7d4227] text-white rounded-lg font-medium transition-colors"
        >
          Create Tour
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            type="text"
            placeholder="Search tours..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#944F2E] focus:border-transparent"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#944F2E] focus:border-transparent"
          >
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="ready">Ready for Review</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
          <input
            type="text"
            placeholder="Filter by city..."
            value={cityFilter}
            onChange={(e) => setCityFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#944F2E] focus:border-transparent"
          />
        </div>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#944F2E] mb-4"></div>
            <p className="text-gray-600 font-medium">Loading tours...</p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Results count */}
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-gray-600">
              {data?.total || 0} tour{data?.total !== 1 ? 's' : ''} found
            </p>
          </div>

          {/* Tours list */}
          {data?.tours && data.tours.length > 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-200">
              {data.tours.map((tour) => (
                <Link
                  key={tour.id}
                  to={`/tours/${tour.id}`}
                  className="block p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-gray-900 truncate">
                        {tour.name}
                      </h3>
                      <div className="mt-1 flex items-center gap-4 text-sm text-gray-600">
                        <span>
                          {tour.city && tour.neighborhood
                            ? `${tour.neighborhood}, ${tour.city}`
                            : tour.city || tour.neighborhood || 'No location'}
                        </span>
                        <span>•</span>
                        <span>
                          {tour.siteCount} {tour.siteCount === 1 ? 'site' : 'sites'}
                        </span>
                        {(tour.averageRating || tour.calculatedRating) && (
                          <>
                            <span>•</span>
                            <span>
                              {(tour.averageRating || tour.calculatedRating)?.toFixed(1)} ★
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {(() => {
                        const statusDisplay = getStatusDisplay(tour.status);
                        return (
                          <span className={`px-3 py-1 text-xs font-medium rounded-full ${statusDisplay.className}`}>
                            {statusDisplay.label}
                          </span>
                        );
                      })()}
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          handleDelete(tour);
                        }}
                        disabled={deleteMutation.isPending}
                        className="px-3 py-1.5 bg-white hover:bg-red-50 text-red-600 text-sm font-medium rounded-md border border-red-200 transition-colors disabled:opacity-50"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">No tours found</h3>
              <p className="text-gray-600 mb-6">Get started by creating your first tour</p>
              <Link
                to="/tours/new"
                className="inline-flex items-center px-6 py-2.5 bg-[#944F2E] hover:bg-[#7d4227] text-white rounded-lg font-medium transition-colors"
              >
                Create Tour
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
