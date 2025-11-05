import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { adminFeedbackApi, adminUsersApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import toast from 'react-hot-toast';
import type { Feedback } from '../types';

export default function Issues() {
  const queryClient = useQueryClient();
  const { user: currentUser } = useAuth();
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [tourFilter, setTourFilter] = useState('');
  const [siteFilter, setSiteFilter] = useState('');
  const [reviewedByFilter, setReviewedByFilter] = useState('');
  const [editingNotes, setEditingNotes] = useState<number | null>(null);
  const [notesDraft, setNotesDraft] = useState('');
  const [currentPage, setCurrentPage] = useState(0);
  const ITEMS_PER_PAGE = 100;

  // Fetch issues
  const { data, isLoading, error: issuesError } = useQuery({
    queryKey: ['issues', statusFilter, tourFilter, siteFilter],
    queryFn: () =>
      adminFeedbackApi.list({
        feedback_type: 'issue',
        status: statusFilter || undefined,
        tour_id: tourFilter || undefined,
        site_id: siteFilter || undefined,
        limit: 500,
      }),
    retry: false,
  });

  // Fetch admin users for reviewed_by dropdown
  const { data: usersData } = useQuery({
    queryKey: ['adminUsers'],
    queryFn: () => adminUsersApi.list({ role: 'admin', limit: 100 }),
    retry: false,
  });

  // Sort users to put current user first
  const sortedUsers = useMemo(() => {
    if (!usersData?.users || !currentUser) return [];
    const users = [...usersData.users];
    const currentUserIndex = users.findIndex(u => u.id === currentUser.id);
    if (currentUserIndex > 0) {
      const [currentUserObj] = users.splice(currentUserIndex, 1);
      users.unshift(currentUserObj);
    }
    return users;
  }, [usersData?.users, currentUser]);

  // Filter by severity and reviewed_by (client-side)
  const filteredIssues = useMemo(() => {
    if (!data?.feedback) return [];
    let filtered = data.feedback;

    // Severity filter
    if (severityFilter) {
      if (severityFilter === 'not_set') {
        filtered = filtered.filter((f) => !f.issueDetail?.severity);
      } else {
        filtered = filtered.filter((f) => f.issueDetail?.severity === severityFilter);
      }
    }

    // Reviewed by filter
    if (reviewedByFilter) {
      if (reviewedByFilter === 'me') {
        filtered = filtered.filter((f) => f.reviewedBy === currentUser?.id);
      } else if (reviewedByFilter === 'unassigned') {
        filtered = filtered.filter((f) => !f.reviewedBy);
      } else {
        filtered = filtered.filter((f) => f.reviewedBy === Number(reviewedByFilter));
      }
    }

    return filtered;
  }, [data?.feedback, severityFilter, reviewedByFilter, currentUser?.id]);

  // Paginate
  const paginatedIssues = useMemo(() => {
    const start = currentPage * ITEMS_PER_PAGE;
    return filteredIssues.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredIssues, currentPage]);

  const totalPages = Math.ceil(filteredIssues.length / ITEMS_PER_PAGE);

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { status?: string; adminNotes?: string } }) =>
      adminFeedbackApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issues'] });
      toast.success('Issue updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to update issue');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminFeedbackApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issues'] });
      toast.success('Issue deleted successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to delete issue');
    },
  });

  const handleStatusChange = (issueId: number, newStatus: string) => {
    updateMutation.mutate({ id: issueId, data: { status: newStatus } });
  };

  const handleSeverityChange = (issue: Feedback, newSeverity: string) => {
    // TODO: Backend doesn't support updating severity yet
    // This would need a new endpoint: PUT /api/admin/feedback/:id/severity
    toast.error('Severity update not yet implemented in backend');
  };

  const handleSaveNotes = (issueId: number) => {
    updateMutation.mutate(
      { id: issueId, data: { adminNotes: notesDraft, status: 'reviewed' } },
      {
        onSuccess: () => {
          setEditingNotes(null);
          setNotesDraft('');
        },
      }
    );
  };

  const handleCancelNotes = () => {
    setEditingNotes(null);
    setNotesDraft('');
  };

  const handleEditNotes = (issue: Feedback) => {
    setEditingNotes(issue.id);
    setNotesDraft(issue.adminNotes || '');
  };

  const handleDelete = (issueId: number, issueTitle: string) => {
    if (window.confirm(`Are you sure you want to delete this issue: "${issueTitle}"?`)) {
      deleteMutation.mutate(issueId);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-700';
      case 'reviewed':
        return 'bg-blue-100 text-blue-700';
      case 'resolved':
        return 'bg-green-100 text-green-700';
      case 'dismissed':
        return 'bg-gray-100 text-gray-600';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  const getSeverityBadgeClass = (severity: string | null) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-700';
      case 'medium':
        return 'bg-yellow-100 text-yellow-700';
      case 'low':
        return 'bg-green-100 text-green-700';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  // Show errors if any
  if (issuesError) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-red-500">
          <p className="font-bold mb-2">Error loading issues:</p>
          <p>{String(issuesError)}</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#8B6F47] mb-4"></div>
          <p className="text-gray-600 font-medium">Loading issues...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Issues</h1>
          <div className="text-sm text-gray-600 mt-1">
            <strong>{filteredIssues.length}</strong> issues
            {statusFilter && ` • Status: ${statusFilter}`}
            {severityFilter && ` • Severity: ${severityFilter === 'not_set' ? 'Not Set' : severityFilter}`}
          </div>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-3 items-center bg-white p-3 rounded-lg border border-gray-200">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-gray-600 font-medium">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setCurrentPage(0);
            }}
            className="border border-gray-300 rounded px-2 py-1 text-sm focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
          >
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="reviewed">Reviewed</option>
            <option value="resolved">Resolved</option>
            <option value="dismissed">Dismissed</option>
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm">
          <span className="text-gray-600 font-medium">Severity:</span>
          <select
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value);
              setCurrentPage(0);
            }}
            className="border border-gray-300 rounded px-2 py-1 text-sm focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
          >
            <option value="">All</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="not_set">Not Set</option>
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm">
          <span className="text-gray-600 font-medium">Tour ID:</span>
          <div className="relative">
            <input
              type="text"
              value={tourFilter}
              onChange={(e) => {
                setTourFilter(e.target.value);
                setCurrentPage(0);
              }}
              placeholder="UUID"
              className="border border-gray-300 rounded px-2 py-1 pr-8 text-sm w-64 focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
            />
            {tourFilter && (
              <button
                onClick={() => {
                  setTourFilter('');
                  setCurrentPage(0);
                }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            )}
          </div>
        </label>

        <label className="flex items-center gap-2 text-sm">
          <span className="text-gray-600 font-medium">Site ID:</span>
          <div className="relative">
            <input
              type="text"
              value={siteFilter}
              onChange={(e) => {
                setSiteFilter(e.target.value);
                setCurrentPage(0);
              }}
              placeholder="UUID"
              className="border border-gray-300 rounded px-2 py-1 pr-8 text-sm w-64 focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
            />
            {siteFilter && (
              <button
                onClick={() => {
                  setSiteFilter('');
                  setCurrentPage(0);
                }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            )}
          </div>
        </label>

        <label className="flex items-center gap-2 text-sm">
          <span className="text-gray-600 font-medium">Reviewed By:</span>
          <select
            value={reviewedByFilter}
            onChange={(e) => {
              setReviewedByFilter(e.target.value);
              setCurrentPage(0);
            }}
            className="border border-gray-300 rounded px-2 py-1 text-sm focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
          >
            <option value="">All</option>
            <option value="me">Me</option>
            <option value="unassigned">Unassigned</option>
            {sortedUsers.filter(u => u.id !== currentUser?.id).map(user => (
              <option key={user.id} value={user.id}>{user.name}</option>
            ))}
          </select>
        </label>
      </div>

      {/* Issues cards */}
      <div className="space-y-4">
        {paginatedIssues.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center text-gray-500">
            No issues found matching your filters
          </div>
        ) : (
          paginatedIssues.map((issue) => (
            <div
              key={issue.id}
              className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow"
            >
              {/* Card header - Title and actions */}
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-lg font-semibold text-gray-900">
                  {issue.issueDetail?.title || 'Untitled Issue'}
                </h3>
                <button
                  onClick={() => handleDelete(issue.id, issue.issueDetail?.title || 'Untitled')}
                  className="text-gray-400 hover:text-red-600 transition-colors"
                  title="Delete issue"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>

              {/* Comment */}
              {issue.issueDetail?.description && (
                <div className="mb-4 text-sm text-gray-700 bg-gray-50 p-3 rounded">
                  <span className="font-medium text-gray-600">Comment: </span>
                  {issue.issueDetail.description}
                </div>
              )}

              {/* Grid of labeled fields */}
              <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm mb-4">
                <div>
                  <span className="text-gray-600 font-medium">Tour:</span>{' '}
                  {issue.tour ? (
                    <Link
                      to={`/tours/${issue.tour.id}`}
                      className="text-[#8B6F47] hover:underline font-medium"
                    >
                      {issue.tour.name}
                    </Link>
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                  {issue.tour?.city && (
                    <span className="text-gray-500 text-xs ml-1">({issue.tour.city})</span>
                  )}
                </div>

                <div>
                  <span className="text-gray-600 font-medium">Site:</span>{' '}
                  {issue.site ? (
                    <Link
                      to={`/sites/${issue.site.id}`}
                      className="text-[#8B6F47] hover:underline font-medium"
                    >
                      {issue.site.title}
                    </Link>
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                </div>

                <div>
                  <span className="text-gray-600 font-medium">Status:</span>{' '}
                  <select
                    value={issue.status}
                    onChange={(e) => handleStatusChange(issue.id, e.target.value)}
                    className={`inline-flex px-2 py-1 text-xs font-medium rounded-full border-0 focus:ring-2 focus:ring-[#8B6F47] ${getStatusBadgeClass(issue.status)}`}
                  >
                    <option value="pending">Pending</option>
                    <option value="reviewed">Reviewed</option>
                    <option value="resolved">Resolved</option>
                    <option value="dismissed">Dismissed</option>
                  </select>
                </div>

                <div>
                  <span className="text-gray-600 font-medium">Severity:</span>{' '}
                  <select
                    value={issue.issueDetail?.severity || ''}
                    onChange={(e) => handleSeverityChange(issue, e.target.value)}
                    className={`inline-flex px-2 py-1 text-xs font-medium rounded-full border-0 focus:ring-2 focus:ring-[#8B6F47] ${getSeverityBadgeClass(issue.issueDetail?.severity || null)}`}
                  >
                    <option value="">Not Set</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>

                <div>
                  <span className="text-gray-600 font-medium">Submitted By:</span>{' '}
                  {issue.user ? (
                    <span title={issue.user.email}>{issue.user.name}</span>
                  ) : (
                    <span className="text-gray-400 italic">Anonymous</span>
                  )}
                </div>

                <div>
                  <span className="text-gray-600 font-medium">Submitted:</span>{' '}
                  <span className="text-gray-700">{formatDate(issue.createdAt)}</span>
                </div>

                {issue.reviewedAt && (
                  <>
                    <div>
                      <span className="text-gray-600 font-medium">Reviewed By:</span>{' '}
                      {issue.reviewer ? (
                        <span className="text-gray-700">
                          {issue.reviewer.id === currentUser?.id ? 'Me' : issue.reviewer.name}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </div>

                    <div>
                      <span className="text-gray-600 font-medium">Reviewed:</span>{' '}
                      <span className="text-gray-700">{formatDate(issue.reviewedAt)}</span>
                    </div>
                  </>
                )}
              </div>

              {/* Admin Notes */}
              <div className="mt-4 pt-4 border-t border-gray-200">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-600 font-medium text-sm">Admin Notes:</span>
                  {editingNotes !== issue.id && (
                    <button
                      onClick={() => handleEditNotes(issue)}
                      className="text-xs text-[#8B6F47] hover:underline"
                    >
                      Edit
                    </button>
                  )}
                </div>

                {editingNotes === issue.id ? (
                  <div className="space-y-2">
                    <textarea
                      value={notesDraft}
                      onChange={(e) => setNotesDraft(e.target.value)}
                      rows={3}
                      className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
                      placeholder="Add notes about this issue..."
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleSaveNotes(issue.id)}
                        className="px-3 py-1 text-sm bg-[#8B6F47] text-white rounded hover:bg-[#6d5638] transition-colors"
                      >
                        Save
                      </button>
                      <button
                        onClick={handleCancelNotes}
                        className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-gray-700 bg-gray-50 p-3 rounded min-h-[3rem]">
                    {issue.adminNotes || <span className="text-gray-400 italic">No notes yet</span>}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-between items-center bg-white px-4 py-3 rounded-lg border border-gray-200">
          <div className="text-sm text-gray-600">
            Page {currentPage + 1} of {totalPages}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage(currentPage - 1)}
              disabled={currentPage === 0}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage(currentPage + 1)}
              disabled={currentPage >= totalPages - 1}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
