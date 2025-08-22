import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';

// Components
import Login from './components/Login';
import SuperAdminDashboard from './components/SuperAdminDashboard';
import CustomerDashboard from './components/CustomerDashboard';
import LoadingSpinner from './components/LoadingSpinner';

// API Configuration
axios.defaults.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('voiceai_token'));

  useEffect(() => {
    // Check if user is already logged in
    if (token) {
      try {
        const userData = JSON.parse(localStorage.getItem('voiceai_user') || '{}');
        setUser(userData);
      } catch (error) {
        console.error('Invalid user data:', error);
        logout();
      }
    }
    setLoading(false);
  }, [token]);

  const login = (userData, authToken) => {
    localStorage.setItem('voiceai_token', authToken);
    localStorage.setItem('voiceai_user', JSON.stringify(userData));
    axios.defaults.headers.common['Authorization'] = `Bearer ${authToken}`;
    setToken(authToken);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('voiceai_token');
    localStorage.removeItem('voiceai_user');
    delete axios.defaults.headers.common['Authorization'];
    setToken(null);
    setUser(null);
  };

  // Set axios auth header if token exists
  if (token) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-hero-gradient">
        <div className="text-center">
          <LoadingSpinner size="large" />
          <p className="text-white mt-4 text-lg font-medium">Loading VoiceAI Platform...</p>
        </div>
      </div>
    );
  }

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route 
            path="/login" 
            element={
              !user ? (
                <Login onLogin={login} />
              ) : (
                <Navigate to={user.user_type === 'admin' ? '/admin' : '/dashboard'} replace />
              )
            } 
          />
          
          <Route 
            path="/admin/*" 
            element={
              user && user.user_type === 'admin' ? (
                <SuperAdminDashboard user={user} onLogout={logout} />
              ) : (
                <Navigate to="/login" replace />
              )
            } 
          />
          
          <Route 
            path="/dashboard/*" 
            element={
              user && user.user_type === 'tenant' ? (
                <CustomerDashboard user={user} onLogout={logout} />
              ) : (
                <Navigate to="/login" replace />
              )
            } 
          />
          
          <Route 
            path="/" 
            element={
              <Navigate to={
                !user ? '/login' : 
                user.user_type === 'admin' ? '/admin' : '/dashboard'
              } replace />
            } 
          />
          
          {/* Catch all route */}
          <Route 
            path="*" 
            element={<Navigate to="/" replace />} 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;