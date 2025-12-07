import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminNeighborhoodsApi } from '../lib/api';
import { useAuth } from '../lib/auth';

type NeighborhoodFromTour = {
  city: string;
  neighborhood: string;
  tourCount: number;
};

export default function Neighborhoods() {
  const { isAdmin } = useAuth();
  const queryClient = useQueryClient();
  const [cityFilter, setCityFilter] = useState('');
  const [neighborhoodFilter, setNeighborhoodFilter] = useState('');
  const [renamingNeighborhood, setRenamingNeighborhood] = useState<NeighborhoodFromTour | null>(null);
  const [formData, setFormData] = useState({
    city: '',
    neighborhood: '',
  });

  const { data, isLoading } = useQuery({
    queryKey: ['neighborhoods-all-from-tours'],
    queryFn: () => adminNeighborhoodsApi.getAllFromTours(),
    enabled: isAdmin,
  });

  // Filter neighborhoods based on search
  const filteredNeighborhoods = data?.neighborhoods.filter(n => {
    const cityMatch = !cityFilter || n.city.toLowerCase().includes(cityFilter.toLowerCase());
    const neighborhoodMatch = !neighborhoodFilter || n.neighborhood.toLowerCase().includes(neighborhoodFilter.toLowerCase());
    return cityMatch && neighborhoodMatch;
  }) || [];

  const renameMutation = useMutation({
    mutationFn: (data: {
      oldCity: string;
      oldNeighborhood: string;
      newCity: string;
      newNeighborhood: string;
    }) => adminNeighborhoodsApi.rename(data),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['neighborhoods-all-from-tours'] });
      setRenamingNeighborhood(null);
      setFormData({ city: '', neighborhood: '' });

      const toursUpdated = response.toursUpdated || 0;
      const sitesUpdated = response.sitesUpdated || 0;

      alert(`✅ Neighborhood renamed successfully!\n\nUpdated:\n• ${toursUpdated} tours\n• ${sitesUpdated} sites`);
    },
    onError: (error: any) => {
      const errorMsg = error.response?.data?.error || error.message || 'Unknown error';
      alert(`❌ Failed to rename: ${errorMsg}`);
    },
  });

  const handleRename = () => {
    if (renamingNeighborhood && formData.city && formData.neighborhood) {
      renameMutation.mutate({
        oldCity: renamingNeighborhood.city,
        oldNeighborhood: renamingNeighborhood.neighborhood,
        newCity: formData.city,
        newNeighborhood: formData.neighborhood,
      });
    }
  };

  const handleStartRename = (neighborhood: NeighborhoodFromTour) => {
    setRenamingNeighborhood(neighborhood);
    setFormData({
      city: neighborhood.city,
      neighborhood: neighborhood.neighborhood,
    });
  };

  const handleCancel = () => {
    setRenamingNeighborhood(null);
    setFormData({ city: '', neighborhood: '' });
  };

  if (!isAdmin) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">You don't have permission to view this page.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Neighborhoods</h1>
          <p className="text-gray-600 mt-1">
            Consolidate neighborhood names across tours
          </p>
        </div>
      </div>

      {/* Rename Form */}
      {renamingNeighborhood && (
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Rename Neighborhood
          </h2>
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800">
              <strong>Note:</strong> Renaming will automatically update all associated tours and sites.
              This neighborhood currently has <strong>{renamingNeighborhood.tourCount} tour(s)</strong>.
            </p>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                City *
              </label>
              <input
                type="text"
                placeholder="e.g. New York"
                value={formData.city}
                onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Neighborhood *
              </label>
              <input
                type="text"
                placeholder="e.g. Chelsea"
                value={formData.neighborhood}
                onChange={(e) => setFormData({ ...formData, neighborhood: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleRename}
                disabled={!formData.city || !formData.neighborhood}
                className="px-4 py-2 bg-[#8B6F47] hover:bg-[#6F5838] text-white font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Rename
              </button>
              <button
                onClick={handleCancel}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filter by City
            </label>
            <input
              type="text"
              placeholder="Search by city..."
              value={cityFilter}
              onChange={(e) => setCityFilter(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filter by Neighborhood
            </label>
            <input
              type="text"
              placeholder="Search by neighborhood..."
              value={neighborhoodFilter}
              onChange={(e) => setNeighborhoodFilter(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
            />
          </div>
        </div>
      </div>

      {/* Neighborhoods List */}
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#8B6F47] mb-4"></div>
              <p className="text-gray-600 font-medium">Loading neighborhoods...</p>
            </div>
          </div>
        ) : filteredNeighborhoods.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      City
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Neighborhood
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tours
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredNeighborhoods.map((neighborhood, index) => (
                    <tr key={`${neighborhood.city}-${neighborhood.neighborhood}-${index}`} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {neighborhood.city}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm text-gray-900">{neighborhood.neighborhood}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center">
                        <div className="text-sm text-gray-600">{neighborhood.tourCount}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center">
                        <button
                          onClick={() => handleStartRename(neighborhood)}
                          className="text-[#8B6F47] hover:text-[#6F5838] font-medium"
                        >
                          Rename
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
              <p className="text-sm text-gray-600">
                Showing {filteredNeighborhoods.length} of {data?.total || 0} neighborhoods
              </p>
            </div>
          </>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-600">No neighborhoods found</p>
          </div>
        )}
      </div>
    </div>
  );
}
