import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminCitiesApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import { usePresignedUrl } from '../hooks/usePresignedUrl';
import FileUpload from '../components/FileUpload';
import toast from 'react-hot-toast';

type CityFromTour = {
  name: string;
  tourCount: number;
  hasRecord: boolean;
  id: number | null;
  heroImageUrl: string | null;
  heroTitle: string | null;
  heroSubtitle: string | null;
  latitude: number | null;
  longitude: number | null;
  country: string | null;
  stateProvince: string | null;
};

// Component to render city row with presigned URL
function CityRow({
  city,
  onEdit,
  onAdd,
  onDelete
}: {
  city: CityFromTour;
  onEdit: (city: CityFromTour) => void;
  onAdd: (city: CityFromTour) => void;
  onDelete: (id: number) => void;
}) {
  const presignedHeroUrl = usePresignedUrl(city.heroImageUrl);

  return (
    <tr key={city.name} className="hover:bg-gray-50">
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm font-medium text-gray-900">{city.name}</div>
        {city.country && (
          <div className="text-sm text-gray-500">{city.country}</div>
        )}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {city.tourCount} tours
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        {city.hasRecord ? (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
            Has Hero
          </span>
        ) : (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800">
            Needs Hero
          </span>
        )}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        {city.heroImageUrl ? (
          <img
            src={presignedHeroUrl || city.heroImageUrl}
            alt={city.name}
            className="w-16 h-16 object-cover rounded"
          />
        ) : (
          <div className="w-16 h-16 bg-gray-200 rounded flex items-center justify-center text-gray-400 text-xs">
            No Image
          </div>
        )}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
        {city.hasRecord ? (
          <div className="flex gap-2">
            <button
              onClick={() => onEdit(city)}
              className="text-[#8B6F47] hover:text-[#6F5838]"
            >
              Edit
            </button>
            <button
              onClick={() => city.id && onDelete(city.id)}
              className="text-red-600 hover:text-red-800"
            >
              Delete
            </button>
          </div>
        ) : (
          <button
            onClick={() => onAdd(city)}
            className="text-[#8B6F47] hover:text-[#6F5838]"
          >
            + Add Hero
          </button>
        )}
      </td>
    </tr>
  );
}

export default function Cities() {
  const { isAdmin } = useAuth();
  const queryClient = useQueryClient();
  const [cityFilter, setCityFilter] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingCity, setEditingCity] = useState<CityFromTour | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    latitude: 40.7589,
    longitude: -73.9851,
    heroImageUrl: '',
    heroTitle: '',
    heroSubtitle: '',
    country: 'United States',
    stateProvince: '',
  });

  // Get presigned URL for the hero image in the form
  const presignedHeroImageUrl = usePresignedUrl(formData.heroImageUrl);

  const { data, isLoading } = useQuery({
    queryKey: ['cities-all-from-tours'],
    queryFn: () => adminCitiesApi.getAllFromTours(),
    enabled: isAdmin,
  });

  // Filter cities based on search
  const filteredCities = data?.filter(c => {
    const nameMatch = !cityFilter || c.name.toLowerCase().includes(cityFilter.toLowerCase());
    return nameMatch;
  }) || [];

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => adminCitiesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cities-all-from-tours'] });
      setShowCreateForm(false);
      resetForm();
      toast.success('City created successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to create city');
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: { id: number; updates: Partial<typeof formData> }) =>
      adminCitiesApi.update(data.id, data.updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cities-all-from-tours'] });
      setEditingCity(null);
      resetForm();
      toast.success('City updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to update city');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminCitiesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cities-all-from-tours'] });
      toast.success('City deleted successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to delete city');
    },
  });

  const resetForm = () => {
    setFormData({
      name: '',
      latitude: 40.7589,
      longitude: -73.9851,
      heroImageUrl: '',
      heroTitle: '',
      heroSubtitle: '',
      country: 'United States',
      stateProvince: '',
    });
  };

  const handleCreate = () => {
    if (formData.name && formData.latitude && formData.longitude) {
      createMutation.mutate(formData);
    } else {
      toast.error('Please fill in required fields: name, latitude, longitude');
    }
  };

  const handleUpdate = () => {
    if (editingCity && editingCity.id) {
      updateMutation.mutate({
        id: editingCity.id,
        updates: formData,
      });
    }
  };

  const handleEdit = (city: CityFromTour) => {
    setEditingCity(city);
    setFormData({
      name: city.name,
      latitude: city.latitude || 40.7589,
      longitude: city.longitude || -73.9851,
      heroImageUrl: city.heroImageUrl || '',
      heroTitle: city.heroTitle || '',
      heroSubtitle: city.heroSubtitle || '',
      country: city.country || 'United States',
      stateProvince: city.stateProvince || '',
    });
    setShowCreateForm(false);
  };

  const handleAdd = (city: CityFromTour) => {
    setFormData({
      name: city.name,
      latitude: 40.7589,
      longitude: -73.9851,
      heroImageUrl: '',
      heroTitle: `Explore ${city.name} with Voyana Tours`,
      heroSubtitle: '',
      country: 'United States',
      stateProvince: '',
    });
    setShowCreateForm(true);
    setEditingCity(null);
  };

  const handleDelete = (id: number) => {
    if (window.confirm('Are you sure you want to delete this city? This will soft-delete it (set to inactive).')) {
      deleteMutation.mutate(id);
    }
  };

  const handleCancel = () => {
    setShowCreateForm(false);
    setEditingCity(null);
    resetForm();
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
          <h1 className="text-3xl font-bold text-gray-900">Cities</h1>
          <p className="text-gray-600 mt-1">
            Manage city hero images for the explore screen
          </p>
        </div>
        {!showCreateForm && !editingCity && (
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-4 py-2 bg-[#8B6F47] hover:bg-[#6F5838] text-white font-medium rounded-lg shadow-md hover:shadow-lg transition-all duration-200"
          >
            + Create City
          </button>
        )}
      </div>

      {/* Create/Edit Form */}
      {(showCreateForm || editingCity) && (
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            {editingCity ? 'Edit City' : 'Create City'}
          </h2>

          <div className="grid grid-cols-2 gap-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                City Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
                placeholder="New York"
              />
            </div>

            {/* Country */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Country
              </label>
              <input
                type="text"
                value={formData.country}
                onChange={(e) => setFormData(prev => ({ ...prev, country: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
                placeholder="United States"
              />
            </div>

            {/* State/Province */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                State/Province
              </label>
              <input
                type="text"
                value={formData.stateProvince}
                onChange={(e) => setFormData(prev => ({ ...prev, stateProvince: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
                placeholder="New York"
              />
            </div>

            {/* Latitude */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Latitude <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                step="0.000001"
                value={formData.latitude}
                onChange={(e) => setFormData(prev => ({ ...prev, latitude: parseFloat(e.target.value) }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
                placeholder="40.7589"
              />
            </div>

            {/* Longitude */}
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Longitude <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                step="0.000001"
                value={formData.longitude}
                onChange={(e) => setFormData(prev => ({ ...prev, longitude: parseFloat(e.target.value) }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
                placeholder="-73.9851"
              />
            </div>

            {/* Hero Title */}
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Hero Title
              </label>
              <input
                type="text"
                value={formData.heroTitle}
                onChange={(e) => setFormData(prev => ({ ...prev, heroTitle: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
                placeholder="Explore New York with Voyana Tours"
              />
            </div>

            {/* Hero Subtitle */}
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Hero Subtitle (Optional)
              </label>
              <input
                type="text"
                value={formData.heroSubtitle}
                onChange={(e) => setFormData(prev => ({ ...prev, heroSubtitle: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
                placeholder="Optional subtitle text"
              />
            </div>

            {/* Hero Image Upload */}
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Hero Image
              </label>
              <FileUpload
                type="image"
                folder="city-heroes"
                processImage={true}
                onUploadComplete={(url) => setFormData(prev => ({ ...prev, heroImageUrl: url }))}
              />
              {formData.heroImageUrl && (
                <div className="mt-2">
                  <img
                    src={presignedHeroImageUrl || formData.heroImageUrl}
                    alt="Hero preview"
                    className="w-full object-contain rounded-lg"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Image will be optimized to 1170x2532px (iPhone resolution) and compressed to ~200-500KB
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex gap-3 mt-6">
            <button
              onClick={editingCity ? handleUpdate : handleCreate}
              disabled={createMutation.isPending || updateMutation.isPending}
              className="px-4 py-2 bg-[#8B6F47] hover:bg-[#6F5838] text-white font-medium rounded-lg shadow-md hover:shadow-lg transition-all duration-200 disabled:opacity-50"
            >
              {editingCity ? 'Update' : 'Create'}
            </button>
            <button
              onClick={handleCancel}
              className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg transition-all duration-200"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 p-4">
        <input
          type="text"
          placeholder="Search cities..."
          value={cityFilter}
          onChange={(e) => setCityFilter(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
        />
      </div>

      {/* Cities Table */}
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading cities...</div>
        ) : filteredCities.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No cities found</div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  City
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tours
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Hero Image
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredCities.map((city) => (
                <CityRow
                  key={city.name}
                  city={city}
                  onEdit={handleEdit}
                  onAdd={handleAdd}
                  onDelete={handleDelete}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
