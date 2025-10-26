import { useAuth } from '../lib/auth';

export default function Profile() {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
          👤 My Profile
        </h1>
        <p className="text-gray-600 mt-1">View your account information</p>
      </div>

      {/* Profile Card */}
      <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-gray-200/50 overflow-hidden">
        {/* Header accent */}
        <div className="h-2 bg-gradient-to-r from-blue-600 to-indigo-600"></div>

        <div className="p-8 space-y-8">
          {/* User Identity Section */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-2xl">👤</span>
              User Information
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </label>
                <div className="text-lg font-semibold text-gray-900">{user.name}</div>
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </label>
                <div className="text-lg text-gray-900">{user.email}</div>
              </div>
            </div>
          </div>

          {/* Account Details Section */}
          <div className="space-y-4 pt-6 border-t border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-2xl">⚙️</span>
              Account Details
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </label>
                <div>
                  <span
                    className={`inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold ${
                      user.role === 'admin'
                        ? 'bg-purple-100 text-purple-800'
                        : 'bg-blue-100 text-blue-800'
                    }`}
                  >
                    {user.role === 'admin' ? '⭐ Admin' : '✏️ Creator'}
                  </span>
                </div>
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-500 uppercase tracking-wider">
                  Account Status
                </label>
                <div>
                  {user.is_active ? (
                    <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold bg-green-100 text-green-800">
                      ✅ Active
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold bg-red-100 text-red-800">
                      ❌ Inactive
                    </span>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-500 uppercase tracking-wider">
                  Email Verification
                </label>
                <div>
                  {user.email_verified ? (
                    <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold bg-green-100 text-green-800">
                      ✅ Verified
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold bg-yellow-100 text-yellow-800">
                      ⚠️ Not Verified
                    </span>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-500 uppercase tracking-wider">
                  Member Since
                </label>
                <div className="text-lg text-gray-900">
                  {new Date(user.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Info Note */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <span className="text-2xl">💡</span>
          <div>
            <h3 className="font-semibold text-blue-900 mb-1">Need to update your profile?</h3>
            <p className="text-sm text-blue-800">
              Contact your administrator to change your name, email, or role settings.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
