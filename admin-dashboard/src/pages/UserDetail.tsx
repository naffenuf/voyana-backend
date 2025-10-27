import { useState, FormEvent } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { useAuth } from '../lib/auth';
import { adminUsersApi } from '../lib/api';

export default function UserDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAdmin } = useAuth();
  const isNew = id === 'new';

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    role: 'creator',
  });

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => adminUsersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User created successfully!');
      navigate('/users');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to create user');
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();

    if (!formData.name || !formData.email || !formData.password) {
      toast.error('Name, email, and password are required');
      return;
    }

    if (formData.password.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }

    createMutation.mutate(formData);
  };

  const handleCancel = () => {
    navigate('/users');
  };

  const updateField = (field: keyof typeof formData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  if (!isAdmin) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">You don't have permission to view this page.</p>
      </div>
    );
  }

  if (!isNew) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">User editing is not yet implemented. Use the Users list to view user details.</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Create New User</h1>
          <p className="text-gray-600 mt-1">Add a new user account to the system</p>
        </div>
        <button
          type="button"
          onClick={handleCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-lg transition-all"
        >
          ← Back
        </button>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 p-8 space-y-6">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            required
            value={formData.name}
            onChange={(e) => updateField('name', e.target.value)}
            placeholder="Enter full name..."
            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white"
          />
        </div>

        {/* Email */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Email <span className="text-red-500">*</span>
          </label>
          <input
            type="email"
            required
            value={formData.email}
            onChange={(e) => updateField('email', e.target.value)}
            placeholder="user@example.com"
            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white"
          />
        </div>

        {/* Password */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Password <span className="text-red-500">*</span>
          </label>
          <input
            type="password"
            required
            value={formData.password}
            onChange={(e) => updateField('password', e.target.value)}
            placeholder="Minimum 8 characters..."
            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white"
          />
          <p className="text-xs text-gray-500 mt-1">Must be at least 8 characters long</p>
        </div>

        {/* Role */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Role <span className="text-red-500">*</span>
          </label>
          <select
            value={formData.role}
            onChange={(e) => updateField('role', e.target.value)}
            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent transition-all duration-200 bg-white"
          >
            <option value="creator">✏️ Creator - Can create and manage their own tours</option>
            <option value="viewer">👁️ Viewer - Read-only access</option>
            <option value="admin">⭐ Admin - Full access to all features</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            {formData.role === 'admin' && 'Admins have full access to manage all users, tours, and sites.'}
            {formData.role === 'creator' && 'Creators can create and manage their own tours and sites.'}
            {formData.role === 'viewer' && 'Viewers have read-only access to view content.'}
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-4 border-t border-gray-200">
          <button
            type="button"
            onClick={handleCancel}
            disabled={createMutation.isPending}
            className="flex-1 px-5 py-3 text-sm font-medium text-gray-700 hover:text-gray-900 bg-white hover:bg-gray-50 border border-gray-300 rounded-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="flex-1 px-5 py-3 bg-[#8B6F47] hover:bg-[#6F5838] text-white text-sm font-semibold rounded-lg shadow-md hover:shadow-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {createMutation.isPending ? (
              <span className="flex items-center justify-center gap-2">
                <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Creating User...
              </span>
            ) : (
              'Create User'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
