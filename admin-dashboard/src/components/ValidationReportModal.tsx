import { X, AlertTriangle, CheckCircle, ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'
import { type ValidationSummary } from '../lib/validation'

interface ValidationReportModalProps {
  isOpen: boolean
  onClose: () => void
  validation: ValidationSummary
  tourId?: string
}

export default function ValidationReportModal({
  isOpen,
  onClose,
  validation,
  tourId,
}: ValidationReportModalProps) {
  if (!isOpen) return null

  const { isValid, issueCount, tourIssues, siteIssues } = validation

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div
          className={`flex items-center justify-between px-6 py-4 border-b ${
            isValid ? 'bg-green-50' : 'bg-amber-50'
          }`}
        >
          <div className="flex items-center gap-3">
            {isValid ? (
              <CheckCircle className="w-6 h-6 text-green-600" />
            ) : (
              <AlertTriangle className="w-6 h-6 text-amber-600" />
            )}
            <h2 className="text-xl font-semibold text-gray-900">
              Tour Validation Report
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-full transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isValid ? (
            <div className="text-center py-8">
              <CheckCircle className="w-16 h-16 text-green-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                All Requirements Met
              </h3>
              <p className="text-gray-600">
                This tour has all required fields populated and is ready for the iOS app.
              </p>
            </div>
          ) : (
            <>
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <p className="text-amber-900 font-medium">
                  {issueCount} issue{issueCount !== 1 ? 's' : ''} found
                </p>
                <p className="text-amber-700 text-sm mt-1">
                  The following fields are missing or incomplete. Fix these issues to ensure proper iOS app functionality.
                </p>
              </div>

              {/* Tour Issues */}
              {tourIssues.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    Tour Issues ({tourIssues.length})
                  </h3>
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-2">
                    {tourIssues.map((issue, index) => (
                      <div
                        key={index}
                        className="flex items-start gap-3 text-sm"
                      >
                        <span className="text-red-500 mt-0.5">•</span>
                        <div className="flex-1">
                          <span className="font-medium text-red-900">
                            {issue.label}:
                          </span>{' '}
                          <span className="text-red-700">{issue.message}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <p className="text-sm text-gray-600 italic">
                    Fix these issues on this page by scrolling to the relevant sections above.
                  </p>
                </div>
              )}

              {/* Site Issues */}
              {siteIssues.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    Site Issues ({siteIssues.length} site{siteIssues.length !== 1 ? 's' : ''})
                  </h3>
                  <div className="space-y-4">
                    {siteIssues.map((siteGroup) => (
                      <div
                        key={siteGroup.siteId}
                        className="bg-red-50 border border-red-200 rounded-lg overflow-hidden"
                      >
                        {/* Site Header with Link */}
                        <Link
                          to={`/sites/${siteGroup.siteId}`}
                          className="flex items-center justify-between px-4 py-3 bg-red-100 hover:bg-red-200 transition group"
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-red-900">
                              {siteGroup.siteName}
                            </span>
                            <span className="text-sm text-red-700">
                              ({siteGroup.issues.length} issue{siteGroup.issues.length !== 1 ? 's' : ''})
                            </span>
                          </div>
                          <ExternalLink className="w-4 h-4 text-red-700 group-hover:text-red-900" />
                        </Link>

                        {/* Site Issues List */}
                        <div className="px-4 py-3 space-y-2">
                          {siteGroup.issues.map((issue, index) => (
                            <div
                              key={index}
                              className="flex items-start gap-3 text-sm"
                            >
                              <span className="text-red-500 mt-0.5">•</span>
                              <div className="flex-1">
                                <span className="font-medium text-red-900">
                                  {issue.label}:
                                </span>{' '}
                                <span className="text-red-700">
                                  {issue.message}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                  <p className="text-sm text-gray-600 italic">
                    Click on a site above to open its detail page and fix the missing fields. Use your browser's back button to return to this tour.
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-4 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 hover:bg-gray-300 rounded-md transition font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
