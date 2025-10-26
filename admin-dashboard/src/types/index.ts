// User types
export interface User {
  id: number;
  email: string;
  name: string;
  role: 'admin' | 'creator' | 'viewer';
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

// Tour types
export interface Tour {
  id: string;
  name: string;
  description: string | null;
  city: string | null;
  neighborhood: string | null;
  latitude: number | null;
  longitude: number | null;
  imageUrl: string | null;
  audioUrl: string | null;
  mapImageUrl: string | null;
  musicUrls: string[] | null;
  durationMinutes: number | null;
  distanceMeters: number | null;
  averageRating: number | null;
  ratingCount: number;
  calculatedRating: number | null;
  status: 'draft' | 'live' | 'archived';
  isPublic: boolean;
  ownerId: number;
  ownerName: string | null;
  createdAt: string;
  updatedAt: string;
  publishedAt: string | null;
  siteCount: number;
  sites?: Site[];
  siteIds?: string[];
  distance?: number;
}

// Site types
export interface Site {
  id: string;
  title: string;
  description: string | null;
  latitude: number;
  longitude: number;
  city: string | null;
  neighborhood: string | null;
  imageUrl: string | null;
  audioUrl: string | null;
  webUrl: string | null;
  keywords: string[];
  rating: number | null;
  placeId: string | null;
  formatted_address: string | null;
  types: string[];
  user_ratings_total: number | null;
  phone_number: string | null;
  googlePhotoReferences: string[];
  tourCount: number;
  createdAt: string;
  updatedAt: string;
  distance?: number;
}

// Feedback types
export interface Feedback {
  id: number;
  tourId: string | null;
  siteId: string | null;
  userId: number | null;
  feedbackType: 'issue' | 'rating' | 'comment' | 'suggestion';
  rating: number | null;
  comment: string | null;
  status: 'pending' | 'reviewed' | 'resolved' | 'dismissed';
  adminNotes: string | null;
  createdAt: string;
  reviewedAt: string | null;
  reviewedBy: number | null;
}

// Auth types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: User;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

// API Response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ApiError {
  error: string;
}

// Search/Filter params
export interface TourFilters {
  search?: string;
  status?: string;
  city?: string;
  neighborhood?: string;
  owner_id?: number;
  is_public?: boolean;
  lat?: number;
  lon?: number;
  max_distance?: number;
  limit?: number;
  offset?: number;
}

export interface SiteFilters {
  search?: string;
  city?: string;
  neighborhood?: string;
  lat?: number;
  lon?: number;
  max_distance?: number;
  limit?: number;
  offset?: number;
}

export interface UserFilters {
  search?: string;
  role?: string;
  is_active?: boolean;
  limit?: number;
  offset?: number;
}

export interface FeedbackFilters {
  status?: string;
  feedback_type?: string;
  tour_id?: string;
  site_id?: string;
  limit?: number;
  offset?: number;
}
