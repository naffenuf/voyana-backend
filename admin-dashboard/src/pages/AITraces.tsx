import { useState, useEffect } from 'react';
import { Sparkles, Eye, Filter, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import { adminAiApi } from '../lib/api';
import type { AITrace } from '../types';

export default function AITraces() {
  const [traces, setTraces] = useState<AITrace[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<AITrace | null>(null);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const limit = 50;

  // Filters
  const [promptName, setPromptName] = useState('');
  const [provider, setProvider] = useState('');
  const [status, setStatus] = useState('');

  const loadTraces = async () => {
    setLoading(true);
    try {
      const data = await adminAiApi.listTraces({
        prompt_name: promptName || undefined,
        provider: provider || undefined,
        status: status || undefined,
        limit,
        offset,
      });
      setTraces(data.traces);
      setTotal(data.total);
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Failed to load traces');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTraces();
  }, [offset, promptName, provider, status]);

  const handleViewDetails = async (traceId: string) => {
    try {
      const trace = await adminAiApi.getTrace(traceId);
      setSelectedTrace(trace);
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Failed to load trace details');
    }
  };

  const getStatusBadge = (status: string) => {
    const colors = {
      success: 'bg-green-100 text-green-800',
      error: 'bg-red-100 text-red-800',
      pending: 'bg-yellow-100 text-yellow-800',
    };
    return colors[status as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Traces</h1>
          <p className="text-gray-600 mt-1">View and analyze AI prompt executions</p>
        </div>
        <button
          onClick={loadTraces}
          disabled={loading}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow-sm border">
        <div className="flex items-center space-x-2 mb-3">
          <Filter className="w-4 h-4 text-gray-600" />
          <h3 className="font-medium text-gray-900">Filters</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Prompt Name</label>
            <input
              type="text"
              value={promptName}
              onChange={(e) => {
                setPromptName(e.target.value);
                setOffset(0);
              }}
              placeholder="Filter by prompt name..."
              className="w-full px-3 py-2 border rounded-md text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <select
              value={provider}
              onChange={(e) => {
                setProvider(e.target.value);
                setOffset(0);
              }}
              className="w-full px-3 py-2 border rounded-md text-sm"
            >
              <option value="">All Providers</option>
              <option value="openai">OpenAI</option>
              <option value="grok">Grok</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setOffset(0);
              }}
              className="w-full px-3 py-2 border rounded-md text-sm"
            >
              <option value="">All Statuses</option>
              <option value="success">Success</option>
              <option value="error">Error</option>
              <option value="pending">Pending</option>
            </select>
          </div>
        </div>
      </div>

      {/* Traces Table */}
      <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : traces.length === 0 ? (
          <div className="text-center py-12">
            <Sparkles className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-600">No traces found</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Prompt</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Provider</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Latency</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tokens</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {traces.map((trace) => (
                    <tr key={trace.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">
                        {new Date(trace.createdAt).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {trace.promptName}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 uppercase">
                        {trace.provider}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusBadge(trace.status)}`}>
                          {trace.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {trace.metadata.latency ? `${trace.metadata.latency.toFixed(2)}s` : '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {trace.metadata.tokens_total || '-'}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handleViewDetails(trace.id)}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
              <div className="text-sm text-gray-700">
                Showing {offset + 1} to {Math.min(offset + limit, total)} of {total} traces
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                  className="px-3 py-1 text-sm border rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
                >
                  Previous
                </button>
                <button
                  onClick={() => setOffset(offset + limit)}
                  disabled={offset + limit >= total}
                  className="px-3 py-1 text-sm border rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Detail Modal */}
      {selectedTrace && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b">
              <h2 className="text-xl font-semibold">Trace Details</h2>
              <button
                onClick={() => setSelectedTrace(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-700">Prompt Name</h4>
                  <p className="mt-1 text-sm text-gray-900">{selectedTrace.promptName}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-700">Provider / Model</h4>
                  <p className="mt-1 text-sm text-gray-900">{selectedTrace.provider} / {selectedTrace.model}</p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-700">Status</h4>
                  <span className={`inline-block mt-1 px-2 py-1 text-xs font-medium rounded-full ${getStatusBadge(selectedTrace.status)}`}>
                    {selectedTrace.status}
                  </span>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-700">Latency</h4>
                  <p className="mt-1 text-sm text-gray-900">
                    {selectedTrace.metadata.latency?.toFixed(3)}s
                  </p>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">System Prompt</h4>
                <pre className="bg-gray-50 p-3 rounded text-xs overflow-x-auto border">
                  {selectedTrace.systemPrompt}
                </pre>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">User Prompt</h4>
                <pre className="bg-gray-50 p-3 rounded text-xs overflow-x-auto border">
                  {selectedTrace.userPrompt}
                </pre>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Response</h4>
                <pre className="bg-gray-50 p-3 rounded text-xs overflow-x-auto border whitespace-pre-wrap">
                  {selectedTrace.response}
                </pre>
              </div>

              {selectedTrace.errorMessage && (
                <div>
                  <h4 className="text-sm font-medium text-red-700 mb-2">Error</h4>
                  <pre className="bg-red-50 p-3 rounded text-xs overflow-x-auto border border-red-200 text-red-900">
                    {selectedTrace.errorMessage}
                  </pre>
                </div>
              )}

              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Metadata</h4>
                <pre className="bg-gray-50 p-3 rounded text-xs overflow-x-auto border">
                  {JSON.stringify(selectedTrace.metadata, null, 2)}
                </pre>
              </div>

              {selectedTrace.rawRequest && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Raw Request</h4>
                  <pre className="bg-gray-50 p-3 rounded text-xs overflow-x-auto border">
                    {JSON.stringify(selectedTrace.rawRequest, null, 2)}
                  </pre>
                </div>
              )}

              {selectedTrace.rawResponse && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Raw Response</h4>
                  <pre className="bg-gray-50 p-3 rounded text-xs overflow-x-auto border">
                    {JSON.stringify(selectedTrace.rawResponse, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="flex justify-end px-6 py-4 border-t">
              <button
                onClick={() => setSelectedTrace(null)}
                className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
