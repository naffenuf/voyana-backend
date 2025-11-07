import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { useState, useRef, useEffect } from 'react';

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const feedbackRef = useRef<HTMLDivElement>(null);
  const adminRef = useRef<HTMLDivElement>(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (feedbackRef.current && !feedbackRef.current.contains(event.target as Node)) {
        setFeedbackOpen(false);
      }
      if (adminRef.current && !adminRef.current.contains(event.target as Node)) {
        setAdminOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close dropdowns on navigation
  useEffect(() => {
    setFeedbackOpen(false);
    setAdminOpen(false);
  }, [location.pathname]);

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `relative px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
      isActive
        ? 'bg-[#8B6F47] text-white shadow-md'
        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
    }`;

  const dropdownButtonClass = (isOpen: boolean, hasActiveChild: boolean) =>
    `relative px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer ${
      hasActiveChild
        ? 'bg-[#8B6F47] text-white shadow-md'
        : isOpen
        ? 'bg-gray-100 text-gray-900'
        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
    }`;

  const dropdownItemClass = ({ isActive }: { isActive: boolean }) =>
    `block px-4 py-2 text-sm ${
      isActive
        ? 'bg-[#8B6F47] text-white'
        : 'text-gray-700 hover:bg-gray-100'
    }`;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Navigation */}
      <nav className="bg-[#F6EDD9]/95 backdrop-blur-lg shadow-lg border-b border-gray-200/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center space-x-8">
              {/* Logo */}
              <div className="flex items-center space-x-3">
                <img
                  src="/VoyanaLogoNoName.jpg"
                  alt="Voyana Logo"
                  className="w-14 h-14 object-contain"
                />
                <div>
                  <h1 className="text-xl font-bold text-gray-900">
                    Voyana
                  </h1>
                  <p className="text-xs text-[#8B6F47] font-medium">Admin Portal</p>
                </div>
              </div>

              {/* Navigation Links */}
              <div className="flex space-x-1 items-center">
                <NavLink to="/tours" className={navLinkClass}>
                  <span>Tours</span>
                </NavLink>
                <NavLink to="/sites" className={navLinkClass}>
                  <span>Sites</span>
                </NavLink>
                <NavLink to="/heat-map" className={navLinkClass}>
                  <span>Heat Map</span>
                </NavLink>

                {user?.role === 'admin' && (
                  <>
                    {/* Feedback Dropdown */}
                    <div className="relative" ref={feedbackRef}>
                      <button
                        onClick={() => setFeedbackOpen(!feedbackOpen)}
                        className={dropdownButtonClass(
                          feedbackOpen,
                          location.pathname.startsWith('/tour-ratings') ||
                          location.pathname.startsWith('/issues') ||
                          location.pathname.startsWith('/improvements') ||
                          location.pathname.startsWith('/top-tours')
                        )}
                      >
                        <span>Feedback ▾</span>
                      </button>
                      {feedbackOpen && (
                        <div className="absolute left-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                          <NavLink
                            to="/tour-ratings"
                            className={dropdownItemClass}
                          >
                            Tour Ratings
                          </NavLink>
                          <NavLink
                            to="/issues"
                            className={dropdownItemClass}
                          >
                            Issues
                          </NavLink>
                          <NavLink
                            to="/improvements"
                            className={dropdownItemClass}
                          >
                            Improvements
                          </NavLink>
                          <NavLink
                            to="/top-tours"
                            className={dropdownItemClass}
                          >
                            Top Tours
                          </NavLink>
                        </div>
                      )}
                    </div>

                    {/* Admin Dropdown */}
                    <div className="relative" ref={adminRef}>
                      <button
                        onClick={() => setAdminOpen(!adminOpen)}
                        className={dropdownButtonClass(
                          adminOpen,
                          location.pathname.startsWith('/users') ||
                          location.pathname.startsWith('/neighborhoods') ||
                          location.pathname.startsWith('/cities') ||
                          location.pathname.startsWith('/default-music') ||
                          location.pathname.startsWith('/ai-traces') ||
                          location.pathname.startsWith('/api-keys')
                        )}
                      >
                        <span>Admin ▾</span>
                      </button>
                      {adminOpen && (
                        <div className="absolute left-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                          <NavLink
                            to="/users"
                            className={dropdownItemClass}
                          >
                            Users
                          </NavLink>
                          <NavLink
                            to="/neighborhoods"
                            className={dropdownItemClass}
                          >
                            Neighborhoods
                          </NavLink>
                          <NavLink
                            to="/cities"
                            className={dropdownItemClass}
                          >
                            Cities
                          </NavLink>
                          <NavLink
                            to="/default-music"
                            className={dropdownItemClass}
                          >
                            Default Music
                          </NavLink>
                          <NavLink
                            to="/ai-traces"
                            className={dropdownItemClass}
                          >
                            AI Traces
                          </NavLink>
                          <NavLink
                            to="/api-keys"
                            className={dropdownItemClass}
                          >
                            API Keys
                          </NavLink>
                        </div>
                      )}
                    </div>
                  </>
                )}

                <NavLink to="/profile" className={navLinkClass}>
                  <span>Profile</span>
                </NavLink>
              </div>
            </div>

            {/* User menu */}
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <div className="font-semibold text-gray-900 text-sm">{user?.name}</div>
                <div className="text-xs">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    user?.role === 'admin'
                      ? 'bg-purple-100 text-purple-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {user?.role === 'admin' ? '⭐ Admin' : '✏️ Creator'}
                  </span>
                </div>
              </div>
              <button
                onClick={logout}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-lg transition-all duration-200"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
