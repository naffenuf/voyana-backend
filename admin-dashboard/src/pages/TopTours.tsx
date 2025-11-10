import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { adminToursApi } from '../lib/api';
import StarRating from '../components/StarRating';

export default function TopTours() {
  const [minRatings, setMinRatings] = useState<number>(0);
  const [cityFilter, setCityFilter] = useState('');
  const [sortBy, setSortBy] = useState<'rating' | 'count' | 'recent'>('rating');

  // Fetch all tours
  const { data, isLoading } = useQuery({
    queryKey: ['admin-tours'],
    queryFn: () => adminToursApi.list({ limit: 500 }),
  });

  // Filter and sort tours
  const processedTours = useMemo(() => {
    if (!data?.tours) return [];

    let filtered = data.tours
      .filter((tour) => tour.ratingCount && tour.ratingCount >= minRatings)
      .filter((tour) => !cityFilter || tour.city === cityFilter);

    // Sort
    filtered.sort((a, b) => {
      if (sortBy === 'rating') {
        return (b.averageRating || 0) - (a.averageRating || 0);
      } else if (sortBy === 'count') {
        return (b.ratingCount || 0) - (a.ratingCount || 0);
      } else {
        // recent - would need lastRatedAt field from backend, fallback to rating
        return (b.averageRating || 0) - (a.averageRating || 0);
      }
    });

    return filtered;
  }, [data?.tours, minRatings, cityFilter, sortBy]);

  // Calculate stats
  const stats = useMemo(() => {
    if (!data?.tours) return { totalTours: 0, totalRatings: 0, overallAvg: 0 };

    const toursWithRatings = data.tours.filter((t) => t.ratingCount && t.ratingCount > 0);
    const totalRatings = toursWithRatings.reduce((sum, t) => sum + (t.ratingCount || 0), 0);
    const weightedSum = toursWithRatings.reduce(
      (sum, t) => sum + (t.averageRating || 0) * (t.ratingCount || 0),
      0
    );
    const overallAvg = totalRatings > 0 ? weightedSum / totalRatings : 0;

    return {
      totalTours: toursWithRatings.length,
      totalRatings,
      overallAvg,
    };
  }, [data?.tours]);

  // Get unique cities
  const cities = useMemo(() => {
    if (!data?.tours) return [];
    const citySet = new Set(data.tours.map((t) => t.city).filter(Boolean));
    return Array.from(citySet).sort();
  }, [data?.tours]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Loading tours...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with inline stats */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Top Tours</h1>
          <div className="flex items-center gap-4 mt-1 text-sm text-gray-600">
            <span>
              <strong>{stats.totalTours}</strong> tours with ratings
            </span>
            <span>•</span>
            <span>
              <strong>{stats.totalRatings}</strong> total ratings
            </span>
            <span>•</span>
            <span>
              Overall avg: <StarRating rating={stats.overallAvg} showValue />
            </span>
          </div>
        </div>
      </div>

      {/* Compact filter bar */}
      <div className="flex gap-3 items-center bg-white p-3 rounded-lg border border-gray-200">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-gray-600 font-medium">Min ratings:</span>
          <select
            value={minRatings}
            onChange={(e) => setMinRatings(Number(e.target.value))}
            className="border border-gray-300 rounded px-2 py-1 text-sm focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
          >
            <option value="0">All</option>
            <option value="3">3+</option>
            <option value="5">5+</option>
            <option value="10">10+</option>
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm">
          <span className="text-gray-600 font-medium">City:</span>
          <select
            value={cityFilter}
            onChange={(e) => setCityFilter(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-sm focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
          >
            <option value="">All cities</option>
            {cities.map((city) => (
              <option key={city || ''} value={city || ''}>
                {city}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm">
          <span className="text-gray-600 font-medium">Sort by:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'rating' | 'count' | 'recent')}
            className="border border-gray-300 rounded px-2 py-1 text-sm focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
          >
            <option value="rating">Highest rated</option>
            <option value="count">Most ratings</option>
          </select>
        </label>

        <div className="ml-auto text-sm text-gray-600">
          Showing <strong>{processedTours.length}</strong> tours
        </div>
      </div>

      {/* Dense data table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-12">
                  #
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tour Name
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">
                  Rating
                </th>
                <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-24">
                  Count
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-40">
                  City
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {processedTours.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    No tours found matching your filters
                  </td>
                </tr>
              ) : (
                processedTours.map((tour, index) => (
                  <tr
                    key={tour.id}
                    className="hover:bg-gray-50 transition-colors cursor-pointer"
                  >
                    <td className="px-4 py-2 text-sm text-gray-500">
                      #{index + 1}
                    </td>
                    <td className="px-4 py-2 text-sm">
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/tours/${tour.id}`}
                          className="text-[#8B6F47] hover:underline font-medium"
                        >
                          {tour.name}
                        </Link>
                        {tour.ratingCount && tour.ratingCount >= 25 && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 border border-green-200">
                            Live
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-sm">
                      <StarRating rating={tour.averageRating || 0} showValue />
                    </td>
                    <td className="px-4 py-2 text-sm text-center text-gray-600">
                      {tour.ratingCount}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-600">
                      {tour.city}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
