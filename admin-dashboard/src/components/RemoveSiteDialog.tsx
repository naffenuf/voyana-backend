import { X, AlertTriangle } from 'lucide-react';
import type { Site } from '../types';

interface RemoveSiteDialogProps {
  isOpen: boolean;
  onClose: () => void;
  site: Site;
  tourId?: string;
  onRemoveFromTour?: () => void;
  onDeleteSite: () => void;
}

export default function RemoveSiteDialog({
  isOpen,
  onClose,
  site,
  tourId,
  onRemoveFromTour,
  onDeleteSite,
}: RemoveSiteDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-md w-full overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b bg-amber-50">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-amber-600" />
            <h2 className="text-xl font-semibold text-gray-900">Remove Site</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-full transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <div className="space-y-2">
            <p className="font-medium text-gray-900">{site.title}</p>
            <p className="text-sm text-gray-600">
              Choose an action for this site:
            </p>
          </div>

          <div className="space-y-3">
            {/* Remove from Tour Option (only if in tour context) */}
            {tourId && onRemoveFromTour && (
              <button
                onClick={() => {
                  onRemoveFromTour();
                  onClose();
                }}
                className="w-full p-4 text-left border-2 border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition group"
              >
                <div className="font-medium text-gray-900 group-hover:text-blue-900">
                  Remove from Tour
                </div>
                <div className="text-sm text-gray-600 mt-1">
                  Remove this site from the tour only. The site will remain in the system and can be added to other tours.
                </div>
              </button>
            )}

            {/* Delete Site Option */}
            <button
              onClick={() => {
                onDeleteSite();
                onClose();
              }}
              className="w-full p-4 text-left border-2 border-red-300 rounded-lg hover:border-red-500 hover:bg-red-50 transition group"
            >
              <div className="font-medium text-red-900 group-hover:text-red-700">
                Delete Site
              </div>
              <div className="text-sm text-red-700 mt-1">
                <strong>Permanently delete</strong> this site from the system. This will remove it from all tours and delete all associated S3 images and audio files. This action cannot be undone.
              </div>
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-4 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-md transition"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
