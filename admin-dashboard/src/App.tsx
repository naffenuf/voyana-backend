import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './lib/auth';
import Layout from './components/Layout';
import AdminRoute from './components/AdminRoute';
import Login from './pages/Login';
import Tours from './pages/Tours';
import TourDetail from './pages/TourDetail';
import Sites from './pages/Sites';
import SiteDetail from './pages/SiteDetail';
import Users from './pages/Users';
import UserDetail from './pages/UserDetail';
import Neighborhoods from './pages/Neighborhoods';
import Cities from './pages/Cities';
import Profile from './pages/Profile';
import AITraces from './pages/AITraces';
import HeatMap from './pages/HeatMap';
import ApiKeys from './pages/ApiKeys';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function AppRoutes() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <Login />}
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/tours" replace />} />
        <Route path="tours" element={<Tours />} />
        <Route path="tours/:id" element={<TourDetail />} />
        <Route path="sites" element={<Sites />} />
        <Route path="sites/:id" element={<SiteDetail />} />
        <Route path="heat-map" element={<HeatMap />} />
        <Route path="users" element={<AdminRoute><Users /></AdminRoute>} />
        <Route path="users/:id" element={<AdminRoute><UserDetail /></AdminRoute>} />
        <Route path="neighborhoods" element={<AdminRoute><Neighborhoods /></AdminRoute>} />
        <Route path="cities" element={<AdminRoute><Cities /></AdminRoute>} />
        <Route path="ai-traces" element={<AdminRoute><AITraces /></AdminRoute>} />
        <Route path="api-keys" element={<AdminRoute><ApiKeys /></AdminRoute>} />
        <Route path="profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                style: {
                  background: '#10b981',
                },
              },
              error: {
                style: {
                  background: '#ef4444',
                },
              },
            }}
          />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
