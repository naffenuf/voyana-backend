import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';
import type {
  User,
  Tour,
  Site,
  Feedback,
  Neighborhood,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  TourFilters,
  SiteFilters,
  UserFilters,
  FeedbackFilters,
  NeighborhoodFilters,
  PlacesSearchResponse,
  PlaceDetails,
  PhotoDownloadResponse,
  AITrace,
  AITraceFilters,
  GenerateDescriptionRequest,
  GenerateDescriptionResponse,
  ApiKey,
  ApiKeyFilters,
  DefaultMusicTrack,
} from '../types';
import { refreshAccessToken } from './auth';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Flag to prevent infinite retry loops
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: any) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });

  failedQueue = [];
};

// Response interceptor to handle errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // If 401 error and we haven't tried refreshing yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // If a refresh is already in progress, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${token}`;
          }
          return api(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Attempt to refresh the token
        const newAccessToken = await refreshAccessToken();

        if (newAccessToken) {
          // Update the authorization header with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          }

          // Process any queued requests with the new token
          processQueue(null, newAccessToken);

          // Retry the original request
          return api(originalRequest);
        } else {
          // Refresh failed, logout user
          processQueue(new Error('Token refresh failed'), null);
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
          return Promise.reject(error);
        }
      } catch (refreshError) {
        // Refresh failed, logout user
        processQueue(refreshError as Error, null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // For all other errors, just reject
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>('/auth/login', data);
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>('/auth/register', data);
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<{ user: User }>('/auth/me');
    return response.data.user;
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  },
};

// Tours API
export const toursApi = {
  list: async (filters?: TourFilters) => {
    const response = await api.get<{ tours: Tour[]; total: number; limit: number; offset: number }>(
      '/api/tours',
      { params: filters }
    );
    return response.data;
  },

  get: async (id: string) => {
    const response = await api.get<{ tour: Tour }>(`/api/tours/${id}`);
    return response.data.tour;
  },

  create: async (data: Partial<Tour>) => {
    const response = await api.post<Tour>('/api/tours', data);
    return response.data;
  },

  update: async (id: string, data: Partial<Tour>) => {
    const response = await api.put<{ tour: Tour }>(`/api/tours/${id}`, data);
    return response.data.tour;
  },

  delete: async (id: string) => {
    await api.delete(`/api/tours/${id}`);
  },

  generateAudioForSites: async (id: string) => {
    const response = await api.post<{
      sitesProcessed: number;
      sitesSkipped: number;
      results: Array<{
        siteId: string;
        siteTitle: string;
        status: 'success' | 'skipped' | 'error';
        audioUrl?: string;
        fromCache?: boolean;
        reason?: string;
        error?: string;
      }>;
    }>(`/api/tours/${id}/generate-audio-for-sites`);
    return response.data;
  },
};

// Admin Tours API
export const adminToursApi = {
  list: async (filters?: TourFilters) => {
    const response = await api.get<{ tours: Tour[]; total: number; limit: number; offset: number }>(
      '/api/admin/tours',
      { params: filters }
    );
    return response.data;
  },

  upload: async (tours: any[]) => {
    const response = await api.post<{
      success: Array<{ tourName: string; tourId: string; sitesCreated: number; status: string }>;
      errors: Array<{ tourName: string; error: string }>;
      summary: { total: number; succeeded: number; failed: number };
    }>('/api/admin/tours/upload', { tours });
    return response.data;
  },
};

// Sites API
export const sitesApi = {
  list: async (filters?: SiteFilters) => {
    const response = await api.get<{ sites: Site[]; total: number; limit: number; offset: number }>(
      '/api/sites',
      { params: filters }
    );
    return response.data;
  },

  get: async (id: string) => {
    const response = await api.get<{ site: Site }>(`/api/sites/${id}`);
    return response.data.site;
  },

  create: async (data: Partial<Site>) => {
    const response = await api.post<{ site: Site }>('/api/sites', data);
    return response.data.site;
  },

  update: async (id: string, data: Partial<Site>) => {
    const response = await api.put<{ site: Site }>(`/api/sites/${id}`, data);
    return response.data.site;
  },

  delete: async (id: string) => {
    await api.delete(`/api/sites/${id}`);
  },
};

// Admin Users API
export const adminUsersApi = {
  list: async (filters?: UserFilters) => {
    const response = await api.get<{ users: User[]; total: number; limit: number; offset: number }>(
      '/api/admin/users',
      { params: filters }
    );
    return response.data;
  },

  get: async (id: number) => {
    const response = await api.get<{ user: User }>(`/api/admin/users/${id}`);
    return response.data.user;
  },

  create: async (data: { name: string; email: string; password: string; role?: string }) => {
    const response = await api.post<{ user: User }>('/api/admin/users', data);
    return response.data.user;
  },

  update: async (id: number, data: Partial<User>) => {
    const response = await api.put<{ user: User }>(`/api/admin/users/${id}`, data);
    return response.data.user;
  },

  updateRole: async (id: number, role: string) => {
    const response = await api.put<{ user: User }>(`/api/admin/users/${id}/role`, { role });
    return response.data.user;
  },

  deactivate: async (id: number) => {
    await api.delete(`/api/admin/users/${id}`);
  },
};

// Admin Feedback API
export const adminFeedbackApi = {
  list: async (filters?: FeedbackFilters) => {
    const response = await api.get<{ feedback: Feedback[]; total: number; limit: number; offset: number }>(
      '/api/admin/feedback',
      { params: filters }
    );
    return response.data;
  },

  get: async (id: number) => {
    const response = await api.get<{ feedback: Feedback }>(`/api/admin/feedback/${id}`);
    return response.data.feedback;
  },

  update: async (id: number, data: { status?: string; adminNotes?: string; reviewedBy?: number }) => {
    const response = await api.put<{ feedback: Feedback }>(`/api/admin/feedback/${id}`, data);
    return response.data.feedback;
  },

  delete: async (id: number) => {
    await api.delete(`/api/admin/feedback/${id}`);
  },

  getStats: async () => {
    const response = await api.get<{
      totalCount: number;
      byStatus: { pending: number; reviewed: number; resolved: number; dismissed: number };
      byType: { issue: number; rating: number; comment: number; suggestion: number };
      averageRating: number | null;
    }>('/api/admin/feedback/stats');
    return response.data;
  },
};

// Admin Photo Submissions API
export const adminPhotoSubmissionsApi = {
  list: async (filters?: FeedbackFilters) => {
    const response = await api.get<{ photos: Feedback[]; total: number; limit: number; offset: number }>(
      '/api/admin/photo-submissions',
      { params: filters }
    );
    return response.data;
  },

  get: async (id: number) => {
    const response = await api.get<{ photo: Feedback }>(`/api/admin/photo-submissions/${id}`);
    return response.data.photo;
  },

  update: async (id: number, data: { status?: string; adminNotes?: string }) => {
    const response = await api.put<{ photo: Feedback }>(`/api/admin/photo-submissions/${id}`, data);
    return response.data.photo;
  },

  approve: async (id: number, options: { replaceImage?: boolean; updateLocation?: boolean }) => {
    const response = await api.post<{ photo: Feedback; site: any }>(
      `/api/admin/photo-submissions/${id}/approve`,
      options
    );
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/api/admin/photo-submissions/${id}`);
  },
};

// Admin Location Data API
export const adminLocationDataApi = {
  list: async (filters?: FeedbackFilters) => {
    const response = await api.get<{ locations: Feedback[]; total: number; limit: number; offset: number }>(
      '/api/admin/location-data',
      { params: filters }
    );
    return response.data;
  },

  get: async (id: number) => {
    const response = await api.get<{ location: Feedback }>(`/api/admin/location-data/${id}`);
    return response.data.location;
  },

  update: async (id: number, data: { status?: string; adminNotes?: string }) => {
    const response = await api.put<{ location: Feedback }>(`/api/admin/location-data/${id}`, data);
    return response.data.location;
  },

  approve: async (id: number) => {
    const response = await api.post<{ location: Feedback; site: any }>(
      `/api/admin/location-data/${id}/approve`
    );
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/api/admin/location-data/${id}`);
  },

  getStats: async () => {
    const response = await api.get<any>('/api/admin/location-data/stats');
    return response.data;
  },
};

// Media API
export const mediaApi = {
  getPresignedUrl: async (url: string): Promise<string> => {
    if (!url) return '';

    // If it's not an S3 URL, return as-is
    if (!url.includes('s3.amazonaws.com') && !url.includes('.s3.')) {
      return url;
    }

    const response = await api.get<{ presignedUrl: string }>(
      '/api/media/presigned-url',
      { params: { url } }
    );
    return response.data.presignedUrl;
  },
};

// Upload API
export const uploadApi = {
  uploadImage: async (file: File, folder?: string, processImage?: boolean) => {
    const formData = new FormData();
    formData.append('file', file);
    if (folder) formData.append('folder', folder);
    if (processImage) formData.append('process', 'true');

    const response = await api.post<{ url: string; filename: string }>(
      '/api/admin/upload/image',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  uploadAudio: async (file: File, folder?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (folder) formData.append('folder', folder);

    const response = await api.post<{ url: string; filename: string }>(
      '/api/admin/upload/audio',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  generateAudio: async (text: string, voiceId?: string) => {
    const response = await api.post<{ url: string; from_cache: boolean }>(
      '/api/admin/upload/generate-audio',
      { text, voice_id: voiceId }
    );
    return response.data;
  },
};

// Google Places API
export const placesApi = {
  search: async (query: string, latitude: number, longitude: number, radius?: number) => {
    const response = await api.get<PlacesSearchResponse>('/api/places/search', {
      params: { query, latitude, longitude, radius },
    });
    return response.data;
  },

  getDetails: async (placeId: string) => {
    const response = await api.get<PlaceDetails>('/api/places/details', {
      params: { place_id: placeId },
    });
    return response.data;
  },

  downloadPhoto: async (photoReference: string, maxWidth?: number, filenamePrefix?: string) => {
    const response = await api.post<PhotoDownloadResponse>('/api/places/download-photo', {
      photo_reference: photoReference,
      max_width: maxWidth,
      filename_prefix: filenamePrefix,
    });
    return response.data;
  },
};

// Admin AI API
export const adminAiApi = {
  generateDescription: async (data: GenerateDescriptionRequest) => {
    const response = await api.post<GenerateDescriptionResponse>(
      '/api/admin/ai/generate-description',
      data
    );
    return response.data;
  },

  listTraces: async (filters?: AITraceFilters) => {
    const response = await api.get<{ traces: AITrace[]; total: number; limit: number; offset: number }>(
      '/api/admin/ai/traces',
      { params: filters }
    );
    return response.data;
  },

  getTrace: async (traceId: string) => {
    const response = await api.get<{ trace: AITrace }>(`/api/admin/ai/traces/${traceId}`);
    return response.data.trace;
  },

  getStats: async () => {
    const response = await api.get<{
      totalTraces: number;
      byProvider: Record<string, number>;
      byStatus: Record<string, number>;
      byPromptName: Record<string, number>;
    }>('/api/admin/ai/traces/stats');
    return response.data;
  },
};

// Admin Neighborhoods API
export const adminNeighborhoodsApi = {
  list: async (filters?: NeighborhoodFilters) => {
    const response = await api.get<{ neighborhoods: Neighborhood[]; total: number; limit: number; offset: number }>(
      '/api/admin/neighborhoods',
      { params: filters }
    );
    return response.data;
  },

  getAllFromTours: async () => {
    const response = await api.get<{
      neighborhoods: Array<{
        city: string;
        neighborhood: string;
        tourCount: number;
        hasDescription: boolean;
        description: string | null;
        descriptionId: number | null;
        createdAt?: string;
        updatedAt?: string;
      }>;
      total: number;
    }>('/api/admin/neighborhoods/all-from-tours');
    return response.data;
  },

  get: async (id: number) => {
    const response = await api.get<Neighborhood>(`/api/admin/neighborhoods/${id}`);
    return response.data;
  },

  create: async (data: { city: string; neighborhood: string; description: string }) => {
    const response = await api.post<Neighborhood>('/api/admin/neighborhoods', data);
    return response.data;
  },

  update: async (id: number, data: { city?: string; neighborhood?: string; description?: string }) => {
    const response = await api.put<Neighborhood>(`/api/admin/neighborhoods/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/api/admin/neighborhoods/${id}`);
  },
};

// Admin Cities API
export const adminCitiesApi = {
  list: async (filters?: { name?: string; include_inactive?: boolean }) => {
    const response = await api.get<Array<{
      id: number;
      name: string;
      latitude: number;
      longitude: number;
      heroImageUrl: string | null;
      heroTitle: string | null;
      heroSubtitle: string | null;
      country: string | null;
      stateProvince: string | null;
      tourCount: number;
      isActive: boolean;
    }>>('/api/admin/cities', { params: filters });
    return response.data;
  },

  getAllFromTours: async () => {
    const response = await api.get<Array<{
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
    }>>('/api/admin/cities/all-from-tours');
    return response.data;
  },

  get: async (id: number) => {
    const response = await api.get<{
      id: number;
      name: string;
      latitude: number;
      longitude: number;
      heroImageUrl: string | null;
      heroTitle: string | null;
      heroSubtitle: string | null;
      country: string | null;
      stateProvince: string | null;
      timezone: string | null;
      isActive: boolean;
      tourCount: number;
    }>(`/api/admin/cities/${id}`);
    return response.data;
  },

  create: async (data: {
    name: string;
    latitude: number;
    longitude: number;
    heroImageUrl?: string;
    heroTitle?: string;
    heroSubtitle?: string;
    country?: string;
    stateProvince?: string;
    timezone?: string;
  }) => {
    const response = await api.post<{ message: string; city: any }>('/api/admin/cities', data);
    return response.data.city;
  },

  update: async (id: number, data: {
    name?: string;
    latitude?: number;
    longitude?: number;
    heroImageUrl?: string;
    heroTitle?: string;
    heroSubtitle?: string;
    country?: string;
    stateProvince?: string;
    timezone?: string;
    isActive?: boolean;
  }) => {
    const response = await api.put<{ message: string; city: any }>(`/api/admin/cities/${id}`, data);
    return response.data.city;
  },

  delete: async (id: number) => {
    await api.delete(`/api/admin/cities/${id}`);
  },
};

// Admin API Keys API
export const adminApiKeysApi = {
  list: async (filters?: ApiKeyFilters) => {
    const response = await api.get<{ keys: ApiKey[]; total: number; limit: number; offset: number }>(
      '/api/admin/api-keys',
      { params: filters }
    );
    return response.data;
  },

  create: async (data: { name: string; user_id?: number }) => {
    const response = await api.post<{ key: ApiKey }>('/api/admin/api-keys', data);
    return response.data.key;
  },

  update: async (id: number, data: { name?: string; is_active?: boolean }) => {
    const response = await api.patch<{ key: ApiKey }>(`/api/admin/api-keys/${id}`, data);
    return response.data.key;
  },

  delete: async (id: number) => {
    await api.delete(`/api/admin/api-keys/${id}`);
  },
};

// Default Music API
export const defaultMusicApi = {
  list: async (includeInactive = false) => {
    const response = await api.get<{ tracks: DefaultMusicTrack[] }>(
      '/api/default-music',
      { params: { include_inactive: includeInactive } }
    );
    return response.data.tracks;
  },

  get: async (id: string) => {
    const response = await api.get<DefaultMusicTrack>(`/api/default-music/${id}`);
    return response.data;
  },

  create: async (data: { url: string; title?: string; displayOrder?: number; isActive?: boolean }) => {
    const response = await api.post<DefaultMusicTrack>('/api/default-music', data);
    return response.data;
  },

  update: async (id: string, data: { url?: string; title?: string; displayOrder?: number; isActive?: boolean }) => {
    const response = await api.put<DefaultMusicTrack>(`/api/default-music/${id}`, data);
    return response.data;
  },

  delete: async (id: string) => {
    await api.delete(`/api/default-music/${id}`);
  },

  reorder: async (trackIds: string[]) => {
    const response = await api.post<{ success: boolean }>('/api/default-music/reorder', { trackIds });
    return response.data;
  },
};

export default api;
