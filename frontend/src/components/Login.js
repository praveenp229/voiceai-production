import React, { useState } from 'react';
import { Eye, EyeOff, Phone, Lock, User, Building } from 'lucide-react';
import LoadingSpinner from './LoadingSpinner';
import axios from 'axios';

const Login = ({ onLogin }) => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    userType: 'admin' // admin or tenant
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post('/api/auth/login', {
        email: formData.email,
        password: formData.password,
        user_type: formData.userType
      });

      if (response.data.token) {
        // Create user object from response
        const userData = {
          email: formData.email,
          user_type: response.data.user_type,
          name: response.data.name,
          tenant_id: response.data.tenant_id // Add tenant_id for tenant users
        };
        onLogin(userData, response.data.token);
      } else {
        setError(response.data.message || 'Login failed');
      }
    } catch (error) {
      console.error('Login error:', error);
      setError(
        error.response?.data?.message || 
        'Unable to connect to server. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="min-h-screen bg-hero-gradient flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Logo & Header */}
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-white rounded-full flex items-center justify-center shadow-lg mb-6">
            <Phone className="h-8 w-8 text-primary-500" />
          </div>
          <h1 className="text-4xl font-bold text-white font-display mb-2">
            VoiceAI Platform
          </h1>
          <p className="text-orange-100 text-lg">
            Intelligent Dental Appointment Scheduling
          </p>
        </div>

        {/* Login Form */}
        <div className="bg-white rounded-2xl shadow-2xl p-8 space-y-6">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-dark-700 font-display">
              Sign in to your account
            </h2>
            <p className="text-gray-600 mt-2">
              Access your dashboard and manage your voice AI system
            </p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex">
                <div className="text-red-800 text-sm">{error}</div>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* User Type Selection */}
            <div>
              <label className="form-label">Account Type</label>
              <div className="grid grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() => setFormData({...formData, userType: 'admin'})}
                  className={`p-4 rounded-lg border-2 text-left transition-all duration-200 ${
                    formData.userType === 'admin'
                      ? 'border-primary-500 bg-primary-50 text-primary-700'
                      : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                  }`}
                >
                  <User className="h-5 w-5 mb-2" />
                  <div className="font-medium">Super Admin</div>
                  <div className="text-sm opacity-75">Manage all tenants</div>
                </button>
                <button
                  type="button"
                  onClick={() => setFormData({...formData, userType: 'tenant'})}
                  className={`p-4 rounded-lg border-2 text-left transition-all duration-200 ${
                    formData.userType === 'tenant'
                      ? 'border-primary-500 bg-primary-50 text-primary-700'
                      : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                  }`}
                >
                  <Building className="h-5 w-5 mb-2" />
                  <div className="font-medium">Hospital/Clinic</div>
                  <div className="text-sm opacity-75">Manage your data</div>
                </button>
              </div>
            </div>

            {/* Email Field */}
            <div>
              <label htmlFor="email" className="form-label">
                Email
              </label>
              <div className="relative">
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  value={formData.email}
                  onChange={handleInputChange}
                  className="form-input pl-11"
                  placeholder="Enter your email"
                />
                <User className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="form-label">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={formData.password}
                  onChange={handleInputChange}
                  className="form-input pl-11 pr-11"
                  placeholder="Enter your password"
                />
                <Lock className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center space-x-2 py-3"
            >
              {loading ? (
                <>
                  <LoadingSpinner size="small" />
                  <span>Signing in...</span>
                </>
              ) : (
                <span>Sign in</span>
              )}
            </button>
          </form>

          {/* Demo Credentials */}
          <div className="border-t border-gray-200 pt-6">
            <div className="text-center text-sm text-gray-500 mb-3">
              Demo Credentials
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="bg-gray-50 p-3 rounded-lg">
                <div className="font-medium text-gray-700 mb-1">Super Admin</div>
                <div className="text-gray-600">
                  <div>Email: admin@voiceai.com</div>
                  <div>Password: admin123</div>
                </div>
              </div>
              <div className="bg-gray-50 p-3 rounded-lg">
                <div className="font-medium text-gray-700 mb-1">Hospital Demo</div>
                <div className="text-gray-600">
                  <div>Email: admin@demodental.com</div>
                  <div>Password: temp123</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-orange-100 text-sm">
          <p>© 2024 VoiceAI Platform. All rights reserved.</p>
        </div>
      </div>
    </div>
  );
};

export default Login;