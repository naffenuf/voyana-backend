import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../lib/auth';
import { sitesApi } from '../lib/api';
import type { Site } from '../types';

export default function Sites() {
  const { isAdmin } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [cityFilter, setCityFilter] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['sites', search, cityFilter],
    queryFn: () =>
      sitesApi.list({
        search: search || undefined,
        city: cityFilter || undefined,
        limit: 50,
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => sitesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sites'] });
      toast.success('Site deleted successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to delete site');
    },
  });

  const handleDelete = (site: Site) => {
    if (!confirm(`Are you sure you want to delete "${site.title}"?`)) return;
    deleteMutation.mutate(site.id);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Sites</h1>
          <p className="text-gray-600 mt-1">Manage your site collection</p>
        </div>
        {isAdmin && (
          <Link
            to="/sites/new"
            className="px-6 py-2.5 bg-[#944F2E] hover:bg-[#7d4227] text-white rounded-lg font-medium transition-colors"
          >
            Create Site
          </Link>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="text"
            placeholder="Search sites..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#944F2E] focus:border-transparent"
          />
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
            <p className="text-gray-600 font-medium">Loading sites...</p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Results count */}
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-gray-600">
              {data?.total || 0} site{data?.total !== 1 ? 's' : ''} found
            </p>
          </div>

          {/* Sites list */}
          {data?.sites && data.sites.length > 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-200">
              {data.sites.map((site) => (
                <Link
                  key={site.id}
                  to={`/sites/${site.id}`}
                  className="block p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-gray-900 truncate">
                        {site.title}
                      </h3>
                      <div className="mt-1 flex items-center gap-4 text-sm text-gray-600">
                        <span>
                          {site.city && site.neighborhood
                            ? `${site.neighborhood}, ${site.city}`
                            : site.city || site.neighborhood || 'No location'}
                        </span>
                        <span>•</span>
                        <span>
                          {site.tourCount} {site.tourCount === 1 ? 'tour' : 'tours'}
                        </span>
                      </div>
                    </div>
                    {isAdmin && (
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          handleDelete(site);
                        }}
                        disabled={deleteMutation.isPending}
                        className="px-3 py-1.5 bg-white hover:bg-red-50 text-red-600 text-sm font-medium rounded-md border border-red-200 transition-colors disabled:opacity-50"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">No sites found</h3>
              <p className="text-gray-600 mb-6">
                {isAdmin
                  ? 'Get started by creating your first site'
                  : 'No sites are available yet'}
              </p>
              {isAdmin && (
                <Link
                  to="/sites/new"
                  className="inline-flex items-center px-6 py-2.5 bg-[#944F2E] hover:bg-[#7d4227] text-white rounded-lg font-medium transition-colors"
                >
                  Create Site
                </Link>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
