import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminNeighborhoodsApi } from '../lib/api';
import { useAuth } from '../lib/auth';

type NeighborhoodFromTour = {
  city: string;
  neighborhood: string;
  tourCount: number;
  hasDescription: boolean;
  description: string | null;
  descriptionId: number | null;
  createdAt?: string;
  updatedAt?: string;
};

export default function Neighborhoods() {
  const { isAdmin } = useAuth();
  const queryClient = useQueryClient();
  const [cityFilter, setCityFilter] = useState('');
  const [neighborhoodFilter, setNeighborhoodFilter] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingNeighborhood, setEditingNeighborhood] = useState<NeighborhoodFromTour | null>(null);
  const [formData, setFormData] = useState({
    city: '',
    neighborhood: '',
    description: '',
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

  const createMutation = useMutation({
    mutationFn: (data: { city: string; neighborhood: string; description: string }) =>
      adminNeighborhoodsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['neighborhoods-all-from-tours'] });
      setShowCreateForm(false);
      setFormData({ city: '', neighborhood: '', description: '' });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: { id: number; updates: { city?: string; neighborhood?: string; description?: string } }) =>
      adminNeighborhoodsApi.update(data.id, data.updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['neighborhoods-all-from-tours'] });
      setEditingNeighborhood(null);
      setFormData({ city: '', neighborhood: '', description: '' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminNeighborhoodsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['neighborhoods-all-from-tours'] });
    },
  });

  const handleCreate = () => {
    if (formData.city && formData.neighborhood && formData.description) {
      createMutation.mutate(formData);
    }
  };

  const handleUpdate = () => {
    if (editingNeighborhood && editingNeighborhood.descriptionId && formData.city && formData.neighborhood && formData.description) {
      updateMutation.mutate({
        id: editingNeighborhood.descriptionId,
        updates: formData,
      });
    }
  };

  const handleEdit = (neighborhood: NeighborhoodFromTour) => {
    setEditingNeighborhood(neighborhood);
    setFormData({
      city: neighborhood.city,
      neighborhood: neighborhood.neighborhood,
      description: neighborhood.description || '',
    });
    setShowCreateForm(false);
  };

  const handleAdd = (neighborhood: NeighborhoodFromTour) => {
    setFormData({
      city: neighborhood.city,
      neighborhood: neighborhood.neighborhood,
      description: '',
    });
    setShowCreateForm(true);
    setEditingNeighborhood(null);
  };

  const handleDelete = (id: number) => {
    if (window.confirm('Are you sure you want to delete this neighborhood description?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleCancel = () => {
    setShowCreateForm(false);
    setEditingNeighborhood(null);
    setFormData({ city: '', neighborhood: '', description: '' });
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
            Manage neighborhood descriptions for tours
          </p>
        </div>
        {!showCreateForm && !editingNeighborhood && (
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-4 py-2 bg-[#8B6F47] hover:bg-[#6F5838] text-white font-medium rounded-lg shadow-md hover:shadow-lg transition-all duration-200"
          >
            + Create Neighborhood
          </button>
        )}
      </div>

      {/* Create/Edit Form */}
      {(showCreateForm || editingNeighborhood) && (
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            {editingNeighborhood ? 'Edit Neighborhood' : 'Create Neighborhood'}
          </h2>
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
                placeholder="e.g. Chinatown"
                value={formData.neighborhood}
                onChange={(e) => setFormData({ ...formData, neighborhood: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description *
              </label>
              <textarea
                rows={4}
                placeholder="Enter neighborhood description..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent resize-none"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={editingNeighborhood ? handleUpdate : handleCreate}
                disabled={!formData.city || !formData.neighborhood || !formData.description}
                className="px-4 py-2 bg-[#8B6F47] hover:bg-[#6F5838] text-white font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {editingNeighborhood ? 'Update' : 'Create'}
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
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      City
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Neighborhood
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tours
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Description
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredNeighborhoods.map((neighborhood, index) => (
                    <tr key={`${neighborhood.city}-${neighborhood.neighborhood}-${index}`} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {neighborhood.city}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{neighborhood.neighborhood}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-600">{neighborhood.tourCount}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {neighborhood.hasDescription ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            Has Description
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                            Needs Description
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-600 max-w-md truncate">
                          {neighborhood.description || '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {neighborhood.hasDescription ? (
                          <>
                            <button
                              onClick={() => handleEdit(neighborhood)}
                              className="text-[#8B6F47] hover:text-[#6F5838] font-medium mr-4"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => neighborhood.descriptionId && handleDelete(neighborhood.descriptionId)}
                              className="text-red-600 hover:text-red-800 font-medium"
                            >
                              Delete
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => handleAdd(neighborhood)}
                            className="text-[#8B6F47] hover:text-[#6F5838] font-medium"
                          >
                            + Add Description
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
              <p className="text-sm text-gray-600">
                Showing {filteredNeighborhoods.length} of {data?.total || 0} neighborhoods
                {filteredNeighborhoods.filter(n => !n.hasDescription).length > 0 && (
                  <span className="ml-2 text-yellow-600">
                    • {filteredNeighborhoods.filter(n => !n.hasDescription).length} need descriptions
                  </span>
                )}
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
