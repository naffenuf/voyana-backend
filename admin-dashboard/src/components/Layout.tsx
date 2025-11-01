import { Outlet, NavLink } from 'react-router-dom';
import { useAuth } from '../lib/auth';

export default function Layout() {
  const { user, logout } = useAuth();

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `relative px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
      isActive
        ? 'bg-[#8B6F47] text-white shadow-md'
        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
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
              <div className="flex space-x-1">
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
                    <NavLink to="/users" className={navLinkClass}>
                      <span>Users</span>
                    </NavLink>
                    <NavLink to="/neighborhoods" className={navLinkClass}>
                      <span>Neighborhoods</span>
                    </NavLink>
                    <NavLink to="/ai-traces" className={navLinkClass}>
                      <span>AI Traces</span>
                    </NavLink>
                    <NavLink to="/api-keys" className={navLinkClass}>
                      <span>API Keys</span>
                    </NavLink>
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
