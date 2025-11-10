import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { MessageSquare, MapPin, User, Calendar, FileText, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminFeedbackApi, sitesApi } from '../../lib/api';
import type { Feedback } from '../../types';

interface CommentFeedbackCardProps {
  feedback: Feedback;
  onDelete: () => void;
}

export default function CommentFeedbackCard({ feedback, onDelete }: CommentFeedbackCardProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const site = feedback.site;
  const [adminNotes, setAdminNotes] = useState(feedback.adminNotes || '');
  const [isEditingNotes, setIsEditingNotes] = useState(false);
  const [siteDescription, setSiteDescription] = useState('');
  const [isEditingDescription, setIsEditingDescription] = useState(false);
  const descriptionTextareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea when editing description
  useEffect(() => {
    if (isEditingDescription && descriptionTextareaRef.current) {
      const textarea = descriptionTextareaRef.current;
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.max(textarea.scrollHeight, 150)}px`;
    }
  }, [isEditingDescription, siteDescription]);

  const handleDescriptionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setSiteDescription(e.target.value);
    // Auto-resize as user types
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.max(textarea.scrollHeight, 150)}px`;
  };

  // Update mutation (status and notes)
  const updateMutation = useMutation({
    mutationFn: (data: { status?: string; adminNotes?: string }) =>
      adminFeedbackApi.update(feedback.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suggestion-feedback'] });
      toast.success('Feedback updated');
      setIsEditingNotes(false);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to update');
    },
  });

  // Update site description mutation
  const updateSiteDescriptionMutation = useMutation({
    mutationFn: (description: string) =>
      sitesApi.update(feedback.siteId!, { description }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suggestion-feedback'] });
      queryClient.invalidateQueries({ queryKey: ['sites'] });
      toast.success('Site description updated');
      setIsEditingDescription(false);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to update description');
    },
  });

  const handleStatusChange = (newStatus: string) => {
    updateMutation.mutate({ status: newStatus });
  };

  const handleSaveNotes = () => {
    updateMutation.mutate({ adminNotes });
  };

  const handleSaveDescription = () => {
    updateSiteDescriptionMutation.mutate(siteDescription);
  };

  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-800',
    reviewed: 'bg-blue-100 text-blue-800',
    resolved: 'bg-green-100 text-green-800',
    dismissed: 'bg-gray-100 text-gray-800',
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-green-100 rounded-lg">
            <MessageSquare className="w-5 h-5 text-green-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-900">Add Details</h3>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[feedback.status as keyof typeof statusColors]}`}>
                {feedback.status}
              </span>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
              <div className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {new Date(feedback.createdAt).toLocaleDateString()}
              </div>
              {feedback.user && (
                <div className="flex items-center gap-1">
                  <User className="w-4 h-4" />
                  {feedback.user.name || feedback.user.email}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Status dropdown and delete */}
        <div className="flex items-center gap-2">
          <select
            value={feedback.status}
            onChange={(e) => handleStatusChange(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-[#8B6F47] focus:border-[#8B6F47]"
            disabled={updateMutation.isPending}
          >
            <option value="pending">Pending</option>
            <option value="reviewed">Reviewed</option>
            <option value="resolved">Resolved</option>
            <option value="dismissed">Dismissed</option>
          </select>

          <button
            onClick={onDelete}
            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Site and Tour info */}
      {(site || feedback.tour) && (
        <div className="flex items-center gap-4 mb-4 text-sm">
          {site && (
            <button
              onClick={() => navigate(`/sites/${feedback.siteId}`)}
              className="flex items-center gap-1 text-[#8B6F47] hover:underline"
            >
              <MapPin className="w-4 h-4" />
              {site.title}
            </button>
          )}
          {feedback.tour && (
            <button
              onClick={() => navigate(`/tours/${feedback.tourId}`)}
              className="text-gray-600 hover:underline"
            >
              {feedback.tour.name}
            </button>
          )}
        </div>
      )}

      {/* User Details */}
      <div className="mb-4">
        <div className="text-sm font-medium text-gray-700 mb-2">User Feedback</div>
        <div className="p-4 bg-gray-50 rounded-lg">
          <p className="text-gray-700 whitespace-pre-wrap">{feedback.comment || <span className="text-gray-400 italic">No details provided</span>}</p>
        </div>
      </div>

      {/* Editable Site Description */}
      {site && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-medium text-gray-700">Site Description</div>
            {!isEditingDescription && (
              <button
                onClick={() => setIsEditingDescription(true)}
                className="text-sm text-[#8B6F47] hover:underline"
              >
                Edit
              </button>
            )}
          </div>

          {isEditingDescription ? (
            <div className="space-y-2">
              <textarea
                ref={descriptionTextareaRef}
                value={siteDescription}
                onChange={handleDescriptionChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-[#8B6F47] resize-none overflow-hidden"
                style={{ minHeight: '150px' }}
                placeholder="Enter site description..."
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSaveDescription}
                  disabled={updateSiteDescriptionMutation.isPending}
                  className="px-4 py-2 bg-[#8B6F47] text-white rounded-lg hover:bg-[#6B5437] font-medium transition-colors disabled:opacity-50"
                >
                  {updateSiteDescriptionMutation.isPending ? 'Saving...' : 'Save Description'}
                </button>
                <button
                  onClick={() => {
                    setSiteDescription('');
                    setIsEditingDescription(false);
                  }}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
              {siteDescription ? (
                <p className="text-gray-700 text-sm whitespace-pre-wrap">{siteDescription}</p>
              ) : (
                <p className="text-gray-400 italic text-sm">No description yet</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tour Description (if commenting on tour) */}
      {feedback.tour && feedback.tour.description && !site && (
        <div className="mb-4">
          <div className="text-sm font-medium text-gray-700 mb-2">Current Tour Description</div>
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
            <p className="text-gray-700 text-sm whitespace-pre-wrap">{feedback.tour.description}</p>
          </div>
        </div>
      )}

      {/* Admin Notes */}
      <div className="border-t border-gray-200 pt-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <FileText className="w-4 h-4" />
            Admin Notes
          </div>
          {!isEditingNotes && (
            <button
              onClick={() => setIsEditingNotes(true)}
              className="text-sm text-[#8B6F47] hover:underline"
            >
              Edit
            </button>
          )}
        </div>

        {isEditingNotes ? (
          <div className="space-y-2">
            <textarea
              value={adminNotes}
              onChange={(e) => setAdminNotes(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#8B6F47] focus:border-[#8B6F47]"
              rows={3}
              placeholder="Add admin notes..."
            />
            <div className="flex gap-2">
              <button
                onClick={handleSaveNotes}
                disabled={updateMutation.isPending}
                className="px-4 py-2 bg-[#8B6F47] text-white rounded-lg hover:bg-[#6B5437] font-medium transition-colors disabled:opacity-50"
              >
                Save
              </button>
              <button
                onClick={() => {
                  setAdminNotes(feedback.adminNotes || '');
                  setIsEditingNotes(false);
                }}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="text-sm text-gray-600">
            {adminNotes || <span className="text-gray-400 italic">No notes yet</span>}
          </div>
        )}

        {feedback.reviewedBy && feedback.reviewer && (
          <div className="mt-3 text-xs text-gray-500">
            Reviewed by {feedback.reviewer.name || feedback.reviewer.email} on{' '}
            {feedback.reviewedAt && new Date(feedback.reviewedAt).toLocaleString()}
          </div>
        )}
      </div>
    </div>
  );
}
