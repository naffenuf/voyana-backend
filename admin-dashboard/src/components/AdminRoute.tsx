import { Navigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';

/**
 * AdminRoute - Protected route component that requires admin privileges
 *
 * This component provides route-level security by:
 * 1. Checking if user is authenticated
 * 2. Verifying user has admin role
 * 3. Redirecting non-admins to home page
 *
 * Usage:
 *   <Route path="users" element={<AdminRoute><Users /></AdminRoute>} />
 */
export default function AdminRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isAdmin, isLoading } = useAuth();

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#944F2E] mb-4"></div>
          <p className="text-gray-600 font-medium">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Redirect to home if authenticated but not admin
  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  // User is authenticated and admin - render the protected content
  return <>{children}</>;
}
