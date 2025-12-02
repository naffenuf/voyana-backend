import type { Tour } from '../types';
import { getValidationSummary } from '../lib/validation';

interface PublishTourDialogProps {
  tour: Tour;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isPending?: boolean;
}

export default function PublishTourDialog({
  tour,
  isOpen,
  onClose,
  onConfirm,
  isPending = false,
}: PublishTourDialogProps) {
  if (!isOpen) return null;

  const validation = getValidationSummary(tour, tour.sites || []);
  const isDisabled = !validation.isValid;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">
            Publish Tour
          </h3>

          {isDisabled ? (
            <div className="mb-4">
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
                <div className="flex items-start gap-3">
                  <span className="text-amber-600 text-xl">⚠</span>
                  <div>
                    <p className="font-semibold text-amber-900 mb-1">
                      Cannot Publish Incomplete Tour
                    </p>
                    <p className="text-sm text-amber-700">
                      This tour is missing required information and cannot be published yet.
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm font-medium text-gray-700 mb-2">
                  Missing Information ({validation.issueCount} issue{validation.issueCount !== 1 ? 's' : ''}):
                </p>
                <ul className="space-y-1 text-sm text-gray-600">
                  {validation.tourIssues.map((issue, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-gray-400">•</span>
                      <span>{issue.message}</span>
                    </li>
                  ))}
                  {validation.siteIssues.map((siteGroup, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-gray-400">•</span>
                      <span>
                        <strong>{siteGroup.siteName}:</strong>{' '}
                        {siteGroup.issues.map(i => i.label).join(', ')}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div className="mb-6">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <div className="flex items-start gap-3">
                  <span className="text-blue-600 text-xl">ℹ️</span>
                  <div>
                    <p className="font-semibold text-blue-900 mb-1">
                      Ready to Publish
                    </p>
                    <p className="text-sm text-blue-700">
                      This will immediately make "{tour.name}" available to all users in the mobile app.
                    </p>
                  </div>
                </div>
              </div>

              <p className="text-sm text-gray-600">
                Are you sure you want to publish this tour?
              </p>
            </div>
          )}
        </div>

        <div className="bg-gray-50 px-6 py-4 flex justify-end gap-3 rounded-b-lg">
          <button
            onClick={onClose}
            disabled={isPending}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            {isDisabled ? 'Close' : 'Cancel'}
          </button>
          {!isDisabled && (
            <button
              onClick={onConfirm}
              disabled={isPending}
              className="px-4 py-2 text-sm font-medium text-white bg-[#944F2E] hover:bg-[#7d4227] rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPending ? 'Publishing...' : 'Publish Tour'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
