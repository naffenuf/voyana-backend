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
      console.log('Create success');
      queryClient.invalidateQueries({ queryKey: ['neighborhoods-all-from-tours'] });
      setShowCreateForm(false);
      setEditingNeighborhood(null);
      setFormData({ city: '', neighborhood: '', description: '' });
      alert('✅ Neighborhood saved successfully!');
    },
    onError: (error: any) => {
      console.error('Create error', error);
      const errorMsg = error.response?.data?.error || error.message || 'Unknown error';
      alert(`❌ Failed to save: ${errorMsg}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: { id: number; updates: { city?: string; neighborhood?: string; description?: string } }) =>
      adminNeighborhoodsApi.update(data.id, data.updates),
    onSuccess: (response) => {
      console.log('Update success', response);
      queryClient.invalidateQueries({ queryKey: ['neighborhoods-all-from-tours'] });
      setEditingNeighborhood(null);
      setFormData({ city: '', neighborhood: '', description: '' });

      // Show success message with update counts
      const toursUpdated = response.toursUpdated || 0;
      const sitesUpdated = response.sitesUpdated || 0;
      const merged = response.merged || false;

      if (merged) {
        alert(`✅ Merged with existing neighborhood!\n\nUpdated:\n• ${toursUpdated} tours\n• ${sitesUpdated} sites`);
      } else if (toursUpdated > 0 || sitesUpdated > 0) {
        alert(`✅ Neighborhood updated successfully!\n\nUpdated:\n• ${toursUpdated} tours\n• ${sitesUpdated} sites`);
      } else {
        alert('✅ Neighborhood description updated!');
      }
    },
    onError: (error) => {
      console.error('Update error', error);
      alert(`❌ Failed to update: ${error.message || 'Unknown error'}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminNeighborhoodsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['neighborhoods-all-from-tours'] });
    },
  });

  const handleCreate = () => {
    if (formData.city && formData.neighborhood) {
      createMutation.mutate(formData);
    }
  };

  const renameMutation = useMutation({
    mutationFn: (data: {
      oldCity: string;
      oldNeighborhood: string;
      newCity: string;
      newNeighborhood: string;
      description?: string;
    }) => adminNeighborhoodsApi.rename(data),
    onSuccess: (response) => {
      console.log('Rename success', response);
      queryClient.invalidateQueries({ queryKey: ['neighborhoods-all-from-tours'] });
      setEditingNeighborhood(null);
      setFormData({ city: '', neighborhood: '', description: '' });

      // Show success message with update counts
      const toursUpdated = response.toursUpdated || 0;
      const sitesUpdated = response.sitesUpdated || 0;
      const merged = response.merged || false;

      if (merged) {
        alert(`✅ Consolidated neighborhoods!\n\nUpdated:\n• ${toursUpdated} tours\n• ${sitesUpdated} sites`);
      } else if (toursUpdated > 0 || sitesUpdated > 0) {
        alert(`✅ Neighborhood renamed successfully!\n\nUpdated:\n• ${toursUpdated} tours\n• ${sitesUpdated} sites`);
      } else {
        alert('✅ Neighborhood saved!');
      }
    },
    onError: (error: any) => {
      console.error('Rename error', error);
      const errorMsg = error.response?.data?.error || error.message || 'Unknown error';
      alert(`❌ Failed to save: ${errorMsg}`);
    },
  });

  const handleUpdate = () => {
    console.log('handleUpdate called', { editingNeighborhood, formData });
    if (editingNeighborhood && formData.city && formData.neighborhood) {
      if (!editingNeighborhood.descriptionId) {
        // No description exists - use rename endpoint (handles consolidation/merge)
        console.log('Using rename endpoint for neighborhood without description');
        renameMutation.mutate({
          oldCity: editingNeighborhood.city,
          oldNeighborhood: editingNeighborhood.neighborhood,
          newCity: formData.city,
          newNeighborhood: formData.neighborhood,
          description: formData.description,
        });
      } else {
        // Description exists - use update endpoint (also handles cascading)
        console.log('Updating existing description', editingNeighborhood.descriptionId);
        updateMutation.mutate({
          id: editingNeighborhood.descriptionId,
          updates: formData,
        });
      }
    } else {
      console.log('Validation failed', {
        hasEditingNeighborhood: !!editingNeighborhood,
        hasCity: !!formData.city,
        hasNeighborhood: !!formData.neighborhood
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
          {editingNeighborhood && editingNeighborhood.tourCount > 0 && (
            <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>Note:</strong> Changing the city or neighborhood name will automatically update all associated tours and sites.
                This neighborhood currently has <strong>{editingNeighborhood.tourCount} tour(s)</strong>.
              </p>
            </div>
          )}
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
                Description
              </label>
              <textarea
                rows={4}
                placeholder="Enter neighborhood description (optional)..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent resize-none"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={editingNeighborhood ? handleUpdate : handleCreate}
                disabled={!formData.city || !formData.neighborhood}
                className="px-4 py-2 bg-[#8B6F47] hover:bg-[#6F5838] text-white font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Save
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
              <table className="w-full table-fixed">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="w-32 px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      City
                    </th>
                    <th className="w-52 px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Neighborhood
                    </th>
                    <th className="w-16 px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tours
                    </th>
                    <th className="w-36 px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Description
                    </th>
                    <th className="w-32 px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredNeighborhoods.map((neighborhood, index) => (
                    <tr key={`${neighborhood.city}-${neighborhood.neighborhood}-${index}`} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {neighborhood.city}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm text-gray-900 truncate">{neighborhood.neighborhood}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-center">
                        <div className="text-sm text-gray-600">{neighborhood.tourCount}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {neighborhood.hasDescription ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            Has Desc
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                            No Desc
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm text-gray-600 truncate">
                          {neighborhood.description || '-'}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm">
                        <button
                          onClick={() => handleEdit(neighborhood)}
                          className="text-[#8B6F47] hover:text-[#6F5838] font-medium mr-3"
                        >
                          Edit
                        </button>
                        {neighborhood.hasDescription && (
                          <button
                            onClick={() => neighborhood.descriptionId && handleDelete(neighborhood.descriptionId)}
                            className="text-red-600 hover:text-red-800 font-medium"
                          >
                            Delete
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
