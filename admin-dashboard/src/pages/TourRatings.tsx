import React, { useState, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { adminFeedbackApi } from '../lib/api';
import StarRating from '../components/StarRating';
import type { Feedback } from '../types';

export default function TourRatings() {
  const [searchParams] = useSearchParams();
  const [tourFilter, setTourFilter] = useState(searchParams.get('tourId') || '');
  const [ratingFilter, setRatingFilter] = useState('');
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [currentPage, setCurrentPage] = useState(0);
  const ITEMS_PER_PAGE = 100;

  // Update tour filter if URL param changes
  useEffect(() => {
    const tourIdParam = searchParams.get('tourId');
    if (tourIdParam) {
      setTourFilter(tourIdParam);
    }
  }, [searchParams]);

  // Fetch feedback
  const { data, isLoading, error: feedbackError } = useQuery({
    queryKey: ['feedback', tourFilter, ratingFilter],
    queryFn: () =>
      adminFeedbackApi.list({
        feedback_type: 'rating',
        tour_id: tourFilter || undefined,
        limit: 500,
      }),
    retry: false,
  });

  // Filter by rating value (client-side)
  const filteredFeedback = useMemo(() => {
    if (!data?.feedback) return [];
    if (!ratingFilter) return data.feedback;
    return data.feedback.filter((f) => f.rating === Number(ratingFilter));
  }, [data?.feedback, ratingFilter]);

  // Paginate
  const paginatedFeedback = useMemo(() => {
    const start = currentPage * ITEMS_PER_PAGE;
    return filteredFeedback.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredFeedback, currentPage]);

  const totalPages = Math.ceil(filteredFeedback.length / ITEMS_PER_PAGE);

  // Calculate average for filtered tour
  const filteredAverage = useMemo(() => {
    if (!tourFilter || filteredFeedback.length === 0) return null;
    const sum = filteredFeedback.reduce((acc, f) => acc + (f.rating || 0), 0);
    return sum / filteredFeedback.length;
  }, [tourFilter, filteredFeedback]);

  // Get the tour name if filtering
  const filteredTour = useMemo(() => {
    if (!tourFilter || !filteredFeedback.length) return null;
    // Get tour from first feedback item that has it
    const feedbackWithTour = filteredFeedback.find(f => f.tour?.name);
    return feedbackWithTour?.tour || null;
  }, [tourFilter, filteredFeedback]);

  const toggleRow = (id: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Show errors if any
  if (feedbackError) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-red-500">
          <p className="font-bold mb-2">Error loading feedback:</p>
          <p>{String(feedbackError)}</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Loading ratings...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with inline stats */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tour Ratings</h1>
          <div className="flex items-center gap-4 mt-1 text-sm text-gray-600">
            {tourFilter && filteredTour?.name ? (
              <>
                <span>
                  <strong>{filteredTour.name}</strong>
                </span>
                <span>•</span>
                <span>
                  Showing <strong>{filteredFeedback.length}</strong> ratings
                </span>
                {filteredAverage !== null && (
                  <>
                    <span>•</span>
                    <span>
                      Average: <StarRating rating={filteredAverage} showValue />
                    </span>
                  </>
                )}
              </>
            ) : tourFilter ? (
              <span>
                Showing <strong>{filteredFeedback.length}</strong> ratings for tour
              </span>
            ) : (
              <span>
                <strong>{data?.total ?? 0}</strong> total ratings
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Compact filter bar */}
      <div className="flex flex-wrap gap-3 items-center bg-white p-3 rounded-lg border border-gray-200">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-gray-600 font-medium">Tour ID:</span>
          <div className="relative">
            <input
              type="text"
              value={tourFilter}
              onChange={(e) => {
                setTourFilter(e.target.value);
                setCurrentPage(0);
              }}
              placeholder="Enter tour UUID"
              className="border border-gray-300 rounded px-2 py-1 pr-8 text-sm w-80 focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
            />
            {tourFilter && (
              <button
                onClick={() => {
                  setTourFilter('');
                  setCurrentPage(0);
                }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                title="Clear filter"
              >
                ✕
              </button>
            )}
          </div>
        </label>

        <label className="flex items-center gap-2 text-sm">
          <span className="text-gray-600 font-medium">Rating:</span>
          <select
            value={ratingFilter}
            onChange={(e) => {
              setRatingFilter(e.target.value);
              setCurrentPage(0);
            }}
            className="border border-gray-300 rounded px-2 py-1 text-sm focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
          >
            <option value="">All</option>
            <option value="5">5 stars</option>
            <option value="4">4 stars</option>
            <option value="3">3 stars</option>
            <option value="2">2 stars</option>
            <option value="1">1 star</option>
          </select>
        </label>
      </div>

      {/* Dense data table with expandable rows */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tour Name
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">
                  Rating
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-40">
                  User
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-48">
                  Date
                </th>
                <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-12">

                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {paginatedFeedback.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    No ratings found matching your filters
                  </td>
                </tr>
              ) : (
                paginatedFeedback.map((feedback) => (
                  <React.Fragment key={feedback.id}>
                    <tr
                      className="hover:bg-gray-50 transition-colors"
                    >
                      <td className="px-4 py-2 text-sm">
                        {feedback.tour ? (
                          <Link
                            to={`/tours/${feedback.tour.id}`}
                            className="text-[#8B6F47] hover:underline font-medium truncate block max-w-md"
                            title={feedback.tour.name}
                          >
                            {feedback.tour.name}
                          </Link>
                        ) : (
                          <span className="text-gray-400">Unknown Tour</span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-sm">
                        <StarRating rating={feedback.rating || 0} />
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-600">
                        {feedback.user ? (
                          <span title={feedback.user.email}>{feedback.user.name}</span>
                        ) : (
                          <span className="text-gray-400 italic">Anonymous</span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-600">
                        {formatDate(feedback.createdAt)}
                      </td>
                      <td className="px-4 py-2 text-center">
                        {feedback.comment && feedback.comment.trim() && (
                          <button
                            onClick={() => toggleRow(feedback.id)}
                            className="text-gray-400 hover:text-gray-600 transition-colors"
                            title={expandedRows.has(feedback.id) ? 'Hide comment' : 'Show comment'}
                          >
                            {expandedRows.has(feedback.id) ? '▲' : '▼'}
                          </button>
                        )}
                      </td>
                    </tr>
                    {/* Expandable comment row */}
                    {expandedRows.has(feedback.id) && feedback.comment && (
                      <tr className="bg-gray-50">
                        <td colSpan={5} className="px-4 py-3 text-sm text-gray-700">
                          <div className="flex items-start gap-2">
                            <span className="text-gray-500 font-medium">Comment:</span>
                            <span className="flex-1">{feedback.comment}</span>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-between items-center bg-white px-4 py-3 rounded-lg border border-gray-200">
          <div className="text-sm text-gray-600">
            Page {currentPage + 1} of {totalPages}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage(currentPage - 1)}
              disabled={currentPage === 0}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage(currentPage + 1)}
              disabled={currentPage >= totalPages - 1}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
