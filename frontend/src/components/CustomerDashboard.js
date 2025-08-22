import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { 
  Phone, Calendar, Settings, LogOut, Menu, X,
  Activity, CheckCircle, TrendingUp,
  Download, Search, Plus, Edit, Trash2,
  Zap, Key, Webhook, Eye
} from 'lucide-react';
import axios from 'axios';
import LoadingSpinner from './LoadingSpinner';

const CustomerDashboard = ({ user, onLogout }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tenantInfo, setTenantInfo] = useState(null);
  const [stats, setStats] = useState({
    totalCalls: 0,
    scheduledAppointments: 0,
    completedAppointments: 0,
    successRate: 0
  });
  const location = useLocation();

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [appointmentsResponse, statsResponse, tenantResponse] = await Promise.all([
        axios.get(`/api/v1/tenant/${user.tenant_id}/appointments`),
        axios.get(`/api/v1/tenant/${user.tenant_id}/stats`),
        axios.get(`/api/v1/tenant/${user.tenant_id}/info`)
      ]);

      if (appointmentsResponse.data.success) {
        setAppointments(appointmentsResponse.data.appointments);
      }

      if (statsResponse.data.success) {
        setStats(statsResponse.data.stats);
      }

      if (tenantResponse.data.success) {
        setTenantInfo(tenantResponse.data.tenant);
      }
    } catch (error) {
      console.error('Dashboard data fetch error:', error);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const navigation = [
    { name: 'Overview', href: '/dashboard', icon: Activity, current: location.pathname === '/dashboard' },
    { name: 'Appointments', href: '/dashboard/appointments', icon: Calendar, current: location.pathname.startsWith('/dashboard/appointments') },
    { name: 'Call Logs', href: '/dashboard/calls', icon: Phone, current: location.pathname.startsWith('/dashboard/calls') },
    { name: 'Calendar Settings', href: '/dashboard/calendar', icon: Calendar, current: location.pathname.startsWith('/dashboard/calendar') },
    { name: 'Settings', href: '/dashboard/settings', icon: Settings, current: location.pathname.startsWith('/dashboard/settings') },
  ];

  const handleLogout = () => {
    if (window.confirm('Are you sure you want to logout?')) {
      onLogout();
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <LoadingSpinner size="large" />
          <p className="text-gray-600 mt-4 text-lg">Loading Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
        </div>
      )}

      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0 ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="flex items-center justify-between h-16 px-4 bg-hero-gradient">
          <div className="flex items-center space-x-2">
            <Phone className="h-8 w-8 text-white" />
            <span className="text-white font-bold text-lg font-display">VoiceAI</span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-white hover:text-gray-200"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <nav className="mt-8 px-4 space-y-2">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={item.current ? 'nav-link-active' : 'nav-link'}
                onClick={() => setSidebarOpen(false)}
              >
                <Icon className="h-5 w-5 mr-3" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* Tenant Info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
          <div className="mb-4 p-3 bg-primary-50 rounded-lg">
            <p className="text-xs font-medium text-primary-700 uppercase tracking-wide">Your Clinic</p>
            <p className="text-sm font-semibold text-primary-800 truncate">{tenantInfo?.name || user?.name || 'Demo Clinic'}</p>
            <p className="text-xs text-primary-600">ID: {user?.tenant_id}</p>
          </div>
          
          <div className="flex items-center space-x-3 mb-3">
            <div className="w-8 h-8 bg-secondary-500 rounded-full flex items-center justify-center">
              <span className="text-white font-medium text-sm">
                {user?.username?.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-700 truncate">{user?.username}</p>
              <p className="text-xs text-gray-500">Clinic Administrator</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <LogOut className="h-4 w-4 mr-2" />
            Logout
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top navigation */}
        <div className="bg-white shadow-sm border-b border-gray-200">
          <div className="flex items-center justify-between h-16 px-4 lg:px-6">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden text-gray-500 hover:text-gray-700"
              >
                <Menu className="h-6 w-6" />
              </button>
              <h1 className="text-xl font-semibold text-gray-800 font-display">
                {navigation.find(item => item.current)?.name || 'Dashboard'}
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="hidden sm:flex items-center space-x-3">
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-700">{tenantInfo?.name || user?.name || 'Demo Clinic'}</p>
                  <p className="text-xs text-gray-500">{user?.email}</p>
                </div>
                <div className="w-8 h-8 bg-secondary-500 rounded-full flex items-center justify-center">
                  <span className="text-white font-medium text-sm">
                    {user?.email?.charAt(0).toUpperCase()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Overview stats={stats} appointments={appointments} />} />
            <Route path="/appointments" element={<AppointmentsManagement appointments={appointments} onRefresh={fetchDashboardData} />} />
            <Route path="/calls" element={<CallLogs user={user} />} />
            <Route path="/calendar" element={<CalendarSettings user={user} />} />
            <Route path="/settings" element={<TenantSettings user={user} />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

// Overview Component
const Overview = ({ stats, appointments }) => {
  const recentAppointments = appointments.slice(0, 5);

  return (
    <div className="p-6 space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Calls</p>
              <p className="text-3xl font-bold text-primary-600">{stats.totalCalls}</p>
            </div>
            <Phone className="h-8 w-8 text-primary-500" />
          </div>
        </div>

        <div className="stats-card-secondary">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Scheduled</p>
              <p className="text-3xl font-bold text-secondary-700">{stats.scheduledAppointments}</p>
            </div>
            <Calendar className="h-8 w-8 text-secondary-600" />
          </div>
        </div>

        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Completed</p>
              <p className="text-3xl font-bold text-primary-600">{stats.completedAppointments}</p>
            </div>
            <CheckCircle className="h-8 w-8 text-primary-500" />
          </div>
        </div>

        <div className="stats-card-secondary">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Success Rate</p>
              <p className="text-3xl font-bold text-secondary-700">{stats.successRate}%</p>
            </div>
            <TrendingUp className="h-8 w-8 text-secondary-600" />
          </div>
        </div>
      </div>

      {/* Recent Appointments */}
      <div className="card">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-800 font-display">Recent Appointments</h3>
        </div>
        <div className="p-6">
          {recentAppointments.length > 0 ? (
            <div className="space-y-4">
              {recentAppointments.map((appointment, index) => (
                <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-secondary-100 rounded-lg flex items-center justify-center">
                      <Calendar className="h-5 w-5 text-secondary-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-800">{appointment.patient_name || `Patient ${index + 1}`}</p>
                      <p className="text-sm text-gray-500">{appointment.patient_phone || '(555) 123-4567'}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-800">
                      {appointment.appointment_date || '2024-01-15'}
                    </p>
                    <p className="text-sm text-gray-500">
                      {appointment.appointment_time || '10:00 AM'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Calendar className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No recent appointments</p>
              <p className="text-sm text-gray-400 mt-1">Appointments will appear here when patients call</p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card p-6">
          <h4 className="font-semibold text-gray-800 mb-4 font-display">Quick Actions</h4>
          <div className="space-y-3">
            <button className="btn-primary w-full">
              <Plus className="h-4 w-4 mr-2" />
              Test Voice Call
            </button>
            <button className="btn-outline w-full">
              <Download className="h-4 w-4 mr-2" />
              Export Appointments
            </button>
          </div>
        </div>

        <div className="card p-6">
          <h4 className="font-semibold text-gray-800 mb-4 font-display">System Status</h4>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Voice AI System</span>
              <span className="badge badge-success">Active</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Phone Integration</span>
              <span className="badge badge-success">Connected</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Appointment Sync</span>
              <span className="badge badge-success">Online</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Appointments Management Component
const AppointmentsManagement = ({ appointments, onRefresh }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('all');

  const filteredAppointments = appointments.filter(appointment => {
    const matchesSearch = appointment.patient_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         appointment.patient_phone?.includes(searchTerm);
    const matchesStatus = selectedStatus === 'all' || appointment.status === selectedStatus;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-bold text-gray-800 font-display">Appointments</h2>
        <div className="flex space-x-3 mt-4 sm:mt-0">
          <button className="btn-outline">
            <Download className="h-4 w-4 mr-2" />
            Export
          </button>
          <button className="btn-primary">
            <Plus className="h-4 w-4 mr-2" />
            Manual Entry
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4">
        <div className="relative flex-1">
          <Search className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search appointments..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="form-input pl-10"
          />
        </div>
        <select
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
          className="form-input sm:w-48"
        >
          <option value="all">All Status</option>
          <option value="scheduled">Scheduled</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* Appointments Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Patient
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date & Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Service
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredAppointments.length > 0 ? filteredAppointments.map((appointment, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {appointment.patient_name || `Patient ${index + 1}`}
                      </div>
                      <div className="text-sm text-gray-500">
                        {appointment.patient_phone || '(555) 123-4567'}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {appointment.appointment_date || '2024-01-15'}
                    </div>
                    <div className="text-sm text-gray-500">
                      {appointment.appointment_time || '10:00 AM'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {appointment.service_type || 'General Consultation'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`badge ${
                      appointment.status === 'completed' ? 'badge-success' :
                      appointment.status === 'scheduled' ? 'badge-info' :
                      'badge-warning'
                    }`}>
                      {appointment.status || 'scheduled'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end space-x-2">
                      <button className="text-secondary-600 hover:text-secondary-900">
                        <Edit className="h-4 w-4" />
                      </button>
                      <button className="text-red-600 hover:text-red-900">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="5" className="px-6 py-12 text-center">
                    <Calendar className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500">No appointments found</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// Call Logs Component
const CallLogs = ({ user }) => {
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showTestModal, setShowTestModal] = useState(false);
  const [showCallModal, setShowCallModal] = useState(false);
  const [selectedCall, setSelectedCall] = useState(null);
  const [testTranscript, setTestTranscript] = useState('');

  useEffect(() => {
    fetchCalls();
  }, [fetchCalls]);

  const fetchCalls = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/v1/tenant/${user.tenant_id}/calls`);
      if (response.data.success) {
        setCalls(response.data.calls);
      }
    } catch (error) {
      setError('Failed to load call logs');
    } finally {
      setLoading(false);
    }
  };

  const testVoiceAI = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`/api/v1/tenant/${user.tenant_id}/voice/test`, {
        transcript: testTranscript
      });
      
      if (response.data.success) {
        alert('Voice AI test completed! Check the call logs for results.');
        setShowTestModal(false);
        setTestTranscript('');
        fetchCalls();
      }
    } catch (error) {
      alert('Failed to test Voice AI: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const viewCallDetails = (call) => {
    setSelectedCall(call);
    setShowCallModal(true);
  };

  if (loading && calls.length === 0) {
    return (
      <div className="p-6 flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800 font-display">Call Logs & Voice AI</h2>
        <button 
          onClick={() => setShowTestModal(true)}
          className="btn-primary"
        >
          <Plus className="h-4 w-4 mr-2" />
          Test Voice AI
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {/* Call Logs Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Call Details
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  AI Analysis
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Outcome
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {calls.length > 0 ? calls.map((call) => (
                <tr key={call.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {call.caller_phone || 'Unknown Number'}
                      </div>
                      <div className="text-sm text-gray-500">
                        {call.call_duration} • {new Date(call.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">
                      {call.ai_analysis?.patient_name || 'No AI Analysis'}
                    </div>
                    <div className="text-sm text-gray-500">
                      {call.ai_analysis?.service_type || ''}
                    </div>
                    {call.ai_analysis?.confidence_score && (
                      <div className="text-xs text-gray-400">
                        Confidence: {Math.round(call.ai_analysis.confidence_score * 100)}%
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`badge ${
                      call.appointment_created ? 'badge-success' : 
                      call.ai_analysis?.outcome === 'scheduled' ? 'badge-info' :
                      call.ai_analysis?.outcome === 'callback_needed' ? 'badge-warning' :
                      'badge-secondary'
                    }`}>
                      {call.appointment_created ? 'Appointment Created' : 
                       call.ai_analysis?.outcome === 'scheduled' ? 'Ready to Schedule' :
                       call.ai_analysis?.outcome === 'callback_needed' ? 'Callback Needed' :
                       'Information Only'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-2">
                      {call.ai_processed && <span className="badge badge-success">AI Processed</span>}
                      {call.appointment_created && <span className="badge badge-info">Appointment</span>}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button 
                      onClick={() => viewCallDetails(call)}
                      className="text-primary-600 hover:text-primary-900"
                    >
                      <Eye className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="5" className="px-6 py-12 text-center">
                    <Phone className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500">No call logs found</p>
                    <p className="text-sm text-gray-400 mt-1">Call logs will appear here when patients call</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Voice AI Test Modal */}
      {showTestModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setShowTestModal(false)} />
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Test Voice AI Processing</h3>
                <div className="space-y-4">
                  <div>
                    <label className="form-label">Sample Call Transcript</label>
                    <textarea
                      value={testTranscript}
                      onChange={(e) => setTestTranscript(e.target.value)}
                      className="form-input h-32"
                      placeholder="Enter a sample phone call transcript here..."
                    />
                  </div>
                  <div className="text-sm text-gray-500">
                    <strong>Try this sample:</strong> "Hi, I'd like to schedule a cleaning appointment for next week. My name is Jane Doe and my phone number is 555-123-4567. I'm available Tuesday or Thursday afternoon."
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button 
                  onClick={testVoiceAI}
                  disabled={!testTranscript.trim() || loading}
                  className="btn-primary w-full sm:w-auto sm:ml-3"
                >
                  {loading ? <LoadingSpinner size="small" /> : 'Test Voice AI'}
                </button>
                <button 
                  onClick={() => setShowTestModal(false)}
                  className="btn-outline w-full sm:w-auto mt-3 sm:mt-0"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Call Details Modal */}
      {showCallModal && selectedCall && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setShowCallModal(false)} />
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Call Details - {selectedCall.id}</h3>
                
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Call Information */}
                  <div className="space-y-4">
                    <h4 className="font-medium text-gray-800">Call Information</h4>
                    <div className="space-y-2 text-sm">
                      <div><strong>Phone:</strong> {selectedCall.caller_phone}</div>
                      <div><strong>Duration:</strong> {selectedCall.call_duration}</div>
                      <div><strong>Type:</strong> {selectedCall.call_type}</div>
                      <div><strong>Status:</strong> {selectedCall.call_status}</div>
                      <div><strong>Date:</strong> {new Date(selectedCall.created_at).toLocaleString()}</div>
                    </div>
                  </div>

                  {/* AI Analysis */}
                  {selectedCall.ai_analysis && (
                    <div className="space-y-4">
                      <h4 className="font-medium text-gray-800">AI Analysis</h4>
                      <div className="space-y-2 text-sm">
                        <div><strong>Patient:</strong> {selectedCall.ai_analysis.patient_name}</div>
                        <div><strong>Service:</strong> {selectedCall.ai_analysis.service_type}</div>
                        <div><strong>Outcome:</strong> {selectedCall.ai_analysis.outcome}</div>
                        <div><strong>Confidence:</strong> {Math.round(selectedCall.ai_analysis.confidence_score * 100)}%</div>
                        {selectedCall.ai_analysis.notes && (
                          <div><strong>Notes:</strong> {selectedCall.ai_analysis.notes}</div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Transcript */}
                {selectedCall.transcript && (
                  <div className="mt-6">
                    <h4 className="font-medium text-gray-800 mb-2">Call Transcript</h4>
                    <div className="bg-gray-50 p-4 rounded-lg text-sm">
                      {selectedCall.transcript}
                    </div>
                  </div>
                )}

                {/* Appointment Link */}
                {selectedCall.appointment_id && (
                  <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="h-5 w-5 text-green-600" />
                      <span className="text-green-800 font-medium">
                        Appointment automatically created: {selectedCall.appointment_id}
                      </span>
                    </div>
                  </div>
                )}
              </div>
              
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button 
                  onClick={() => setShowCallModal(false)}
                  className="btn-outline w-full sm:w-auto"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Calendar Settings Component
const CalendarSettings = ({ user }) => {
  const [loading, setLoading] = useState(true);
  const [calendarSettings, setCalendarSettings] = useState(null);
  const [availableProviders, setAvailableProviders] = useState({});
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [connectionData, setConnectionData] = useState({});
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchCalendarData();
  }, [fetchCalendarData]);

  const fetchCalendarData = async () => {
    try {
      setLoading(true);
      const [settingsRes, providersRes] = await Promise.all([
        axios.get(`/api/v1/tenant/${user.tenant_id}/calendar/settings`),
        axios.get(`/api/v1/tenant/${user.tenant_id}/calendar/providers`)
      ]);

      if (settingsRes.data.success) {
        setCalendarSettings(settingsRes.data.settings);
      }
      if (providersRes.data.success) {
        setAvailableProviders(providersRes.data.providers);
      }
    } catch (error) {
      setError('Failed to load calendar settings');
    } finally {
      setLoading(false);
    }
  };

  const handleConnectProvider = (provider) => {
    setSelectedProvider(provider);
    setConnectionData({});
    setShowConnectModal(true);
    setError('');
    setSuccess('');
  };

  const handleConnect = async () => {
    try {
      setLoading(true);
      let endpoint = `/api/v1/tenant/${user.tenant_id}/calendar/connect`;
      let payload = {
        provider: selectedProvider,
        ...connectionData
      };

      // Use specific Curve Hero endpoint if selected
      if (selectedProvider === 'curvehero') {
        endpoint = `/api/v1/tenant/${user.tenant_id}/calendar/curvehero/connect`;
        payload = {
          api_key: connectionData.api_key,
          practice_id: connectionData.practice_id,
          payment_integration: connectionData.payment_integration || false
        };
      }

      const response = await axios.post(endpoint, payload);
      
      if (response.data.success) {
        setSuccess(response.data.message);
        setShowConnectModal(false);
        fetchCalendarData();
      }
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to connect calendar');
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async (provider) => {
    if (window.confirm(`Are you sure you want to disconnect ${availableProviders[provider]?.name}?`)) {
      try {
        const response = await axios.delete(`/api/v1/tenant/${user.tenant_id}/calendar/disconnect/${provider}`);
        if (response.data.success) {
          setSuccess(response.data.message);
          fetchCalendarData();
        }
      } catch (error) {
        setError(error.response?.data?.detail || 'Failed to disconnect calendar');
      }
    }
  };

  const handleSync = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`/api/v1/tenant/${user.tenant_id}/calendar/sync`);
      if (response.data.success) {
        setSuccess(`Synced ${response.data.synced_appointments} appointments successfully`);
        fetchCalendarData();
      }
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to sync calendars');
    } finally {
      setLoading(false);
    }
  };

  const connectedCalendars = calendarSettings?.connected_calendars || [];

  if (loading && !calendarSettings) {
    return (
      <div className="p-6 flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800 font-display">Calendar Integration</h2>
        <button 
          onClick={handleSync}
          disabled={loading || connectedCalendars.length === 0}
          className="btn-primary"
        >
          {loading ? <LoadingSpinner size="small" /> : <Zap className="h-4 w-4" />}
          <span className="ml-2">Sync Now</span>
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-green-800 text-sm">{success}</p>
        </div>
      )}

      {/* Connected Calendars */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 font-display">Connected Calendars</h3>
        {connectedCalendars.length > 0 ? (
          <div className="space-y-4">
            {connectedCalendars.map((calendar, index) => (
              <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                    <Calendar className="h-5 w-5 text-primary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-800">{calendar.provider_name}</p>
                    <p className="text-sm text-gray-500">
                      Connected: {new Date(calendar.connected_at).toLocaleDateString()}
                    </p>
                    {calendar.features && (
                      <div className="flex space-x-2 mt-1">
                        {calendar.features.real_time_sync && <span className="badge badge-success">Real-time</span>}
                        {calendar.features.webhook_notifications && <span className="badge badge-info">Webhooks</span>}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="badge badge-success">Connected</span>
                  <button 
                    onClick={() => handleDisconnect(calendar.provider)}
                    className="text-red-600 hover:text-red-900"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <Calendar className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">No calendars connected</p>
          </div>
        )}
      </div>

      {/* Available Providers */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 font-display">Available Calendar Providers</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(availableProviders).map(([key, provider]) => {
            const isConnected = connectedCalendars.some(c => c.provider === key);
            return (
              <div key={key} className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-gray-800">{provider.name}</h4>
                  {key === 'curvehero' && <span className="badge badge-secondary">New!</span>}
                </div>
                <div className="space-y-2 mb-4">
                  <div className="flex items-center text-xs text-gray-500">
                    <Key className="h-3 w-3 mr-1" />
                    {provider.auth_type === 'oauth2' ? 'OAuth 2.0' : 
                     provider.auth_type === 'api_key' ? 'API Key' : 'Basic Auth'}
                  </div>
                  {provider.webhook_support && (
                    <div className="flex items-center text-xs text-gray-500">
                      <Webhook className="h-3 w-3 mr-1" />
                      Webhook Support
                    </div>
                  )}
                  {provider.real_time_sync && (
                    <div className="flex items-center text-xs text-gray-500">
                      <Zap className="h-3 w-3 mr-1" />
                      Real-time Sync
                    </div>
                  )}
                </div>
                <button
                  onClick={() => isConnected ? handleDisconnect(key) : handleConnectProvider(key)}
                  className={isConnected ? "btn-outline w-full" : "btn-primary w-full"}
                >
                  {isConnected ? 'Disconnect' : 'Connect'}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Connection Modal */}
      {showConnectModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setShowConnectModal(false)} />
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Connect {availableProviders[selectedProvider]?.name}
                </h3>
                
                {selectedProvider === 'curvehero' ? (
                  <div className="space-y-4">
                    <div>
                      <label className="form-label">API Key</label>
                      <input
                        type="password"
                        value={connectionData.api_key || ''}
                        onChange={(e) => setConnectionData({...connectionData, api_key: e.target.value})}
                        className="form-input"
                        placeholder="Enter your Curve Hero API key"
                      />
                    </div>
                    <div>
                      <label className="form-label">Practice ID</label>
                      <input
                        type="text"
                        value={connectionData.practice_id || ''}
                        onChange={(e) => setConnectionData({...connectionData, practice_id: e.target.value})}
                        className="form-input"
                        placeholder="Enter your practice ID"
                      />
                    </div>
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        id="payment_integration"
                        checked={connectionData.payment_integration || false}
                        onChange={(e) => setConnectionData({...connectionData, payment_integration: e.target.checked})}
                        className="mr-2"
                      />
                      <label htmlFor="payment_integration" className="text-sm text-gray-700">
                        Enable payment integration
                      </label>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <label className="form-label">Access Token</label>
                      <input
                        type="password"
                        value={connectionData.access_token || ''}
                        onChange={(e) => setConnectionData({...connectionData, access_token: e.target.value})}
                        className="form-input"
                        placeholder="Enter access token"
                      />
                    </div>
                    <div>
                      <label className="form-label">Calendar ID (optional)</label>
                      <input
                        type="text"
                        value={connectionData.calendar_id || ''}
                        onChange={(e) => setConnectionData({...connectionData, calendar_id: e.target.value})}
                        className="form-input"
                        placeholder="Enter calendar ID"
                      />
                    </div>
                  </div>
                )}
              </div>
              
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button onClick={handleConnect} className="btn-primary w-full sm:w-auto sm:ml-3">
                  Connect
                </button>
                <button onClick={() => setShowConnectModal(false)} className="btn-outline w-full sm:w-auto mt-3 sm:mt-0">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Tenant Settings Component
const TenantSettings = ({ user }) => {
  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold text-gray-800 font-display">Settings</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4 font-display">Clinic Information</h3>
          <div className="space-y-4">
            <div>
              <label className="form-label">Clinic Name</label>
              <input
                type="text"
                value={user?.tenant_name || 'Demo Clinic'}
                className="form-input"
                readOnly
              />
            </div>
            <div>
              <label className="form-label">Tenant ID</label>
              <input
                type="text"
                value={user?.tenant_id || 'tenant_0001'}
                className="form-input"
                readOnly
              />
            </div>
          </div>
        </div>

        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4 font-display">Voice AI Settings</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">Voice AI Enabled</span>
              <span className="badge badge-success">Active</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">Auto-scheduling</span>
              <span className="badge badge-success">Enabled</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">Call Recording</span>
              <span className="badge badge-info">Optional</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CustomerDashboard;