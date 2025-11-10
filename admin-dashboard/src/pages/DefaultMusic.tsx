import { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { defaultMusicApi } from '../lib/api';
import type { DefaultMusicTrack } from '../types';
import FileUpload from '../components/FileUpload';
import { usePresignedUrls } from '../hooks/usePresignedUrl';

export default function DefaultMusic() {
  const queryClient = useQueryClient();
  const [playingIndex, setPlayingIndex] = useState<number | null>(null);
  const audioRefs = useRef<(HTMLAudioElement | null)[]>([]);
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [newTrackUrl, setNewTrackUrl] = useState('');
  const [newTrackTitle, setNewTrackTitle] = useState('');

  // Fetch default music tracks
  const { data: tracks = [], isLoading } = useQuery({
    queryKey: ['defaultMusic'],
    queryFn: () => defaultMusicApi.list(false),
  });

  // Get presigned URLs for S3 tracks
  const presignedUrls = usePresignedUrls(tracks.map(t => t.url));

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: { url: string; title?: string }) => defaultMusicApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['defaultMusic'] });
      toast.success('Track added successfully');
      setIsAddingNew(false);
      setNewTrackUrl('');
      setNewTrackTitle('');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to add track');
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<DefaultMusicTrack> }) => {
      // Filter out null values and convert to API-compatible type
      const cleanedData: {
        url?: string;
        title?: string;
        displayOrder?: number;
        isActive?: boolean;
      } = Object.fromEntries(
        Object.entries(data).filter(([_, v]) => v !== null)
      );
      return defaultMusicApi.update(id, cleanedData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['defaultMusic'] });
      toast.success('Track updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to update track');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => defaultMusicApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['defaultMusic'] });
      toast.success('Track deleted successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error || 'Failed to delete track');
    },
  });

  const handleAddTrack = () => {
    setIsAddingNew(true);
  };

  const handleSaveNewTrack = () => {
    if (!newTrackUrl.trim()) {
      toast.error('Please provide a URL for the track');
      return;
    }
    createMutation.mutate({
      url: newTrackUrl.trim(),
      title: newTrackTitle.trim() || undefined
    });
  };

  const handleCancelNewTrack = () => {
    setIsAddingNew(false);
    setNewTrackUrl('');
    setNewTrackTitle('');
  };

  const handleUpdateUrl = (id: string, url: string) => {
    updateMutation.mutate({ id, data: { url } });
  };

  const handleUpdateTitle = (id: string, title: string) => {
    updateMutation.mutate({ id, data: { title } });
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this track?')) {
      deleteMutation.mutate(id);
    }
  };

  const togglePlayPause = (index: number) => {
    const audio = audioRefs.current[index];
    if (!audio) return;

    // Pause any currently playing audio
    if (playingIndex !== null && playingIndex !== index) {
      const currentAudio = audioRefs.current[playingIndex];
      if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
      }
    }

    if (playingIndex === index) {
      audio.pause();
      audio.currentTime = 0;
      setPlayingIndex(null);
    } else {
      audio.play();
      setPlayingIndex(index);
    }
  };

  // Stop audio when component unmounts
  useEffect(() => {
    return () => {
      audioRefs.current.forEach(audio => {
        if (audio) {
          audio.pause();
          audio.currentTime = 0;
        }
      });
    };
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Default Music Tracks</h1>
          <p className="mt-2 text-gray-600">
            These tracks will play as background music for tours that don't have specific music assigned.
          </p>
        </div>
        <button
          onClick={handleAddTrack}
          disabled={createMutation.isPending || isAddingNew}
          className="px-4 py-2 bg-[#8B6F47] text-white rounded-lg hover:bg-[#6d563a] transition-colors disabled:opacity-50"
        >
          + Add Track
        </button>
      </div>

      {/* Tracks List */}
      <div className="bg-white rounded-xl shadow-md overflow-hidden">
        {tracks.length === 0 && !isAddingNew ? (
          <div className="p-8 text-center text-gray-500">
            No default music tracks yet. Add one to get started!
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {/* New Track Form */}
            {isAddingNew && (
              <div className="p-6 bg-blue-50">
                <div className="flex items-start gap-4">
                  {/* Placeholder for play button */}
                  <div className="mt-1 w-10 h-10 flex items-center justify-center text-gray-400 rounded-lg">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/>
                    </svg>
                  </div>

                  {/* New Track Form */}
                  <div className="flex-1 space-y-3">
                    {/* Title */}
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Title (Optional)
                      </label>
                      <input
                        type="text"
                        value={newTrackTitle}
                        onChange={(e) => setNewTrackTitle(e.target.value)}
                        placeholder="Track title..."
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
                      />
                    </div>

                    {/* URL */}
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Audio URL <span className="text-red-500">*</span>
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="url"
                          value={newTrackUrl}
                          onChange={(e) => setNewTrackUrl(e.target.value)}
                          placeholder="https://s3.amazonaws.com/..."
                          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
                        />
                        <FileUpload
                          type="audio"
                          folder="tours/music"
                          onUploadComplete={(url) => setNewTrackUrl(url)}
                          label="Upload"
                          iconOnly
                          uniqueId="new-track-upload"
                        />
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-2 pt-2">
                      <button
                        onClick={handleSaveNewTrack}
                        disabled={createMutation.isPending}
                        className="px-4 py-2 bg-[#8B6F47] text-white rounded-lg hover:bg-[#6d563a] transition-colors disabled:opacity-50"
                      >
                        {createMutation.isPending ? 'Saving...' : 'Save Track'}
                      </button>
                      <button
                        onClick={handleCancelNewTrack}
                        disabled={createMutation.isPending}
                        className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors disabled:opacity-50"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>

                  {/* Placeholder for delete button */}
                  <div className="w-10"></div>
                </div>
              </div>
            )}

            {/* Existing Tracks */}
            {tracks.map((track, index) => (
              <div key={track.id} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex items-start gap-4">
                  {/* Play/Pause Button */}
                  <button
                    type="button"
                    onClick={() => togglePlayPause(index)}
                    disabled={!track.url}
                    className="mt-1 w-10 h-10 flex items-center justify-center text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-30"
                    title={playingIndex === index ? 'Pause' : 'Play'}
                  >
                    {playingIndex === index ? (
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z"/>
                      </svg>
                    )}
                  </button>
                  <audio
                    ref={(el) => { audioRefs.current[index] = el; }}
                    src={presignedUrls[index] || track.url}
                    crossOrigin="anonymous"
                    preload="metadata"
                    onEnded={() => setPlayingIndex(null)}
                    onError={(e) => console.error('Audio error:', e)}
                  />

                  {/* Track Info */}
                  <div className="flex-1 space-y-3">
                    {/* Title */}
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        Title (Optional)
                      </label>
                      <input
                        type="text"
                        value={track.title || ''}
                        onChange={(e) => handleUpdateTitle(track.id, e.target.value)}
                        placeholder="Track title..."
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
                      />
                    </div>

                    {/* URL */}
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        Audio URL
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="url"
                          value={track.url}
                          onChange={(e) => handleUpdateUrl(track.id, e.target.value)}
                          placeholder="https://s3.amazonaws.com/..."
                          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8B6F47] focus:border-transparent"
                        />
                        <FileUpload
                          type="audio"
                          folder="tours/music"
                          onUploadComplete={(newUrl) => handleUpdateUrl(track.id, newUrl)}
                          label="Upload"
                          iconOnly
                          uniqueId={`default-music-upload-${track.id}`}
                        />
                      </div>
                    </div>

                    {/* Metadata */}
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>Order: {track.displayOrder}</span>
                      <span>•</span>
                      <span className={track.isActive ? 'text-green-600 font-medium' : 'text-gray-400'}>
                        {track.isActive ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>

                  {/* Delete Button */}
                  <button
                    type="button"
                    onClick={() => handleDelete(track.id)}
                    disabled={deleteMutation.isPending}
                    className="mt-1 w-10 h-10 flex items-center justify-center text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                    title="Delete track"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex gap-3">
          <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <div className="flex-1">
            <h3 className="text-sm font-medium text-blue-900">How it works</h3>
            <p className="mt-1 text-sm text-blue-700">
              When a tour is played and has no music tracks assigned to it, these default tracks will be played instead.
              Tracks are played in the order shown above. Upload audio files to S3 or provide direct URLs.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
