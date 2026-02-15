import { X, AlertTriangle } from 'lucide-react';
import type { Tour } from '../types';

interface DeleteTourDialogProps {
  isOpen: boolean;
  onClose: () => void;
  tour: Tour;
  onDeleteTourOnly: () => void;
  onDeleteWithSites: () => void;
  isPending?: boolean;
}

export default function DeleteTourDialog({
  isOpen,
  onClose,
  tour,
  onDeleteTourOnly,
  onDeleteWithSites,
  isPending = false,
}: DeleteTourDialogProps) {
  if (!isOpen) return null;

  const siteCount = tour.siteCount || tour.sites?.length || 0;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-md w-full overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b bg-red-50">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-red-600" />
            <h2 className="text-xl font-semibold text-gray-900">Delete Tour</h2>
          </div>
          <button
            onClick={onClose}
            disabled={isPending}
            className="p-1 hover:bg-gray-100 rounded-full transition disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <div className="space-y-2">
            <p className="font-medium text-gray-900">{tour.name}</p>
            <p className="text-sm text-gray-600">
              This tour has <strong>{siteCount} site{siteCount !== 1 ? 's' : ''}</strong>.
              Choose how to handle them:
            </p>
          </div>

          <div className="space-y-3">
            {/* Delete Tour Only Option */}
            <button
              onClick={() => {
                onDeleteTourOnly();
              }}
              disabled={isPending}
              className="w-full p-4 text-left border-2 border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition group disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="font-medium text-gray-900 group-hover:text-blue-900">
                Delete Tour Only
              </div>
              <div className="text-sm text-gray-600 mt-1">
                Delete the tour but <strong>keep the sites</strong> in the system.
                Sites can be added to other tours later.
              </div>
            </button>

            {/* Delete Tour and Sites Option */}
            <button
              onClick={() => {
                onDeleteWithSites();
              }}
              disabled={isPending}
              className="w-full p-4 text-left border-2 border-red-300 rounded-lg hover:border-red-500 hover:bg-red-50 transition group disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="font-medium text-red-900 group-hover:text-red-700">
                Delete Tour and Sites
              </div>
              <div className="text-sm text-red-700 mt-1">
                Delete the tour <strong>and all its sites</strong>. Sites that are
                shared with other tours will be preserved. This cannot be undone.
              </div>
            </button>
          </div>

          {isPending && (
            <div className="flex items-center justify-center py-2">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-red-600"></div>
              <span className="ml-2 text-sm text-gray-600">Deleting...</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-4 border-t bg-gray-50">
          <button
            onClick={onClose}
            disabled={isPending}
            className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-md transition disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
