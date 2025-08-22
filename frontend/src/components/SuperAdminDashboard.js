import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { 
  Building, Phone, Settings, LogOut, Menu, X,
  Plus, Edit, Trash2, Activity, DollarSign,
  Search, Eye, CheckCircle,
  Calendar, Zap, Key, Webhook, ExternalLink
} from 'lucide-react';
import axios from 'axios';
import LoadingSpinner from './LoadingSpinner';
import TenantModal from './TenantModal';

const SuperAdminDashboard = ({ user, onLogout }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState({
    totalTenants: 0,
    activeTenants: 0,
    totalCalls: 0,
    monthlyRevenue: 0
  });
  const location = useLocation();

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [tenantsResponse, statsResponse] = await Promise.all([
        axios.get('/api/v1/admin/tenants'),
        axios.get('/api/v1/admin/stats')
      ]);

      if (tenantsResponse.data.success) {
        setTenants(tenantsResponse.data.tenants);
      }

      if (statsResponse.data.success) {
        setStats(statsResponse.data.stats);
      }
    } catch (error) {
      console.error('Dashboard data fetch error:', error);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const navigation = [
    { name: 'Overview', href: '/admin', icon: Activity, current: location.pathname === '/admin' },
    { name: 'Tenants', href: '/admin/tenants', icon: Building, current: location.pathname.startsWith('/admin/tenants') },
    { name: 'Calendar Management', href: '/admin/calendar', icon: Calendar, current: location.pathname.startsWith('/admin/calendar') },
    { name: 'Calls & Analytics', href: '/admin/analytics', icon: Phone, current: location.pathname.startsWith('/admin/analytics') },
    { name: 'Settings', href: '/admin/settings', icon: Settings, current: location.pathname.startsWith('/admin/settings') },
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
          <p className="text-gray-600 mt-4 text-lg">Loading Admin Dashboard...</p>
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
            <span className="text-white font-bold text-lg font-display">VoiceAI Admin</span>
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

        {/* User Profile & Logout */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
          <div className="flex items-center space-x-3 mb-3">
            <div className="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center">
              <span className="text-white font-medium text-sm">
                {user?.username?.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-700 truncate">{user?.username}</p>
              <p className="text-xs text-gray-500">Super Administrator</p>
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
                  <p className="text-sm font-medium text-gray-700">{user?.username}</p>
                  <p className="text-xs text-gray-500">Super Admin</p>
                </div>
                <div className="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center">
                  <span className="text-white font-medium text-sm">
                    {user?.username?.charAt(0).toUpperCase()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Overview stats={stats} tenants={tenants} />} />
            <Route path="/tenants" element={<TenantsManagement tenants={tenants} onRefresh={fetchDashboardData} />} />
            <Route path="/calendar" element={<AdminCalendarManagement tenants={tenants} />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/settings" element={<AdminSettings />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

// Overview Component
const Overview = ({ stats, tenants }) => {
  const recentTenants = tenants.slice(0, 5);

  return (
    <div className="p-6 space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Tenants</p>
              <p className="text-3xl font-bold text-primary-600">{stats.totalTenants}</p>
            </div>
            <Building className="h-8 w-8 text-primary-500" />
          </div>
        </div>

        <div className="stats-card-secondary">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Active Tenants</p>
              <p className="text-3xl font-bold text-secondary-700">{stats.activeTenants}</p>
            </div>
            <CheckCircle className="h-8 w-8 text-secondary-600" />
          </div>
        </div>

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
              <p className="text-sm font-medium text-gray-600">Monthly Revenue</p>
              <p className="text-3xl font-bold text-secondary-700">${stats.monthlyRevenue}</p>
            </div>
            <DollarSign className="h-8 w-8 text-secondary-600" />
          </div>
        </div>
      </div>

      {/* Recent Tenants */}
      <div className="card">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-800 font-display">Recent Tenants</h3>
        </div>
        <div className="p-6">
          {recentTenants.length > 0 ? (
            <div className="space-y-4">
              {recentTenants.map((tenant) => (
                <div key={tenant.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                      <Building className="h-5 w-5 text-primary-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-800">{tenant.name}</p>
                      <p className="text-sm text-gray-500">{tenant.contact_email}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`badge ${tenant.status === 'active' ? 'badge-success' : 'badge-warning'}`}>
                      {tenant.status}
                    </span>
                    <p className="text-sm text-gray-500 mt-1">{tenant.plan}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Building className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No tenants found</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Tenants Management Component
const TenantsManagement = ({ tenants, onRefresh }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPlan, setSelectedPlan] = useState('all');
  const [showModal, setShowModal] = useState(false);
  const [editingTenant, setEditingTenant] = useState(null);

  const filteredTenants = tenants.filter(tenant => {
    const matchesSearch = tenant.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         tenant.contact_email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesPlan = selectedPlan === 'all' || tenant.plan === selectedPlan;
    return matchesSearch && matchesPlan;
  });

  const handleCreateTenant = async (tenantData) => {
    try {
      const response = await axios.post('/api/v1/admin/tenants', tenantData);
      if (response.data.success) {
        onRefresh(); // Refresh the tenant list
        setShowModal(false);
      }
    } catch (error) {
      throw error;
    }
  };

  const handleEditTenant = async (tenantData) => {
    try {
      const response = await axios.put(`/api/v1/admin/tenants/${editingTenant.id}`, tenantData);
      if (response.data.success) {
        onRefresh(); // Refresh the tenant list
        setShowModal(false);
        setEditingTenant(null);
      }
    } catch (error) {
      throw error;
    }
  };

  const handleDeleteTenant = async (tenantId) => {
    if (window.confirm('Are you sure you want to delete this tenant? This action cannot be undone.')) {
      try {
        const response = await axios.delete(`/api/v1/admin/tenants/${tenantId}`);
        if (response.data.success) {
          onRefresh(); // Refresh the tenant list
        }
      } catch (error) {
        alert('Failed to delete tenant: ' + (error.response?.data?.detail || error.message));
      }
    }
  };

  const openEditModal = (tenant) => {
    setEditingTenant(tenant);
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingTenant(null);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-bold text-gray-800 font-display">Tenant Management</h2>
        <button 
          onClick={() => setShowModal(true)}
          className="btn-primary mt-4 sm:mt-0"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add New Tenant
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4">
        <div className="relative flex-1">
          <Search className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search tenants..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="form-input pl-10"
          />
        </div>
        <select
          value={selectedPlan}
          onChange={(e) => setSelectedPlan(e.target.value)}
          className="form-input sm:w-48"
        >
          <option value="all">All Plans</option>
          <option value="basic">Basic Plan</option>
          <option value="premium">Premium Plan</option>
        </select>
      </div>

      {/* Tenants Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tenant
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Contact
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Plan
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Revenue
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredTenants.map((tenant) => (
                <tr key={tenant.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                        <Building className="h-5 w-5 text-primary-600" />
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">{tenant.name}</div>
                        <div className="text-sm text-gray-500">{tenant.id}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{tenant.contact_email}</div>
                    <div className="text-sm text-gray-500">{tenant.phone}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`badge ${tenant.plan === 'premium' ? 'badge-primary' : 'badge-info'}`}>
                      {tenant.plan}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`badge ${tenant.status === 'active' ? 'badge-success' : 'badge-warning'}`}>
                      {tenant.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ${tenant.monthly_fee}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end space-x-2">
                      <button 
                        className="text-primary-600 hover:text-primary-900"
                        title="View Details"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                      <button 
                        onClick={() => openEditModal(tenant)}
                        className="text-gray-600 hover:text-gray-900"
                        title="Edit Tenant"
                      >
                        <Edit className="h-4 w-4" />
                      </button>
                      <button 
                        onClick={() => handleDeleteTenant(tenant.id)}
                        className="text-red-600 hover:text-red-900"
                        title="Delete Tenant"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Tenant Modal */}
      <TenantModal
        isOpen={showModal}
        onClose={closeModal}
        onSave={editingTenant ? handleEditTenant : handleCreateTenant}
        tenant={editingTenant}
      />
    </div>
  );
};

// Analytics Component
const Analytics = () => {
  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold text-gray-800 font-display">Calls & Analytics</h2>
      <div className="card p-8 text-center">
        <Phone className="h-16 w-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-800 mb-2">Analytics Dashboard</h3>
        <p className="text-gray-600">Detailed call analytics and reports will be displayed here.</p>
      </div>
    </div>
  );
};

// Admin Calendar Management Component
const AdminCalendarManagement = ({ tenants }) => {
  const [loading, setLoading] = useState(false);
  const [availableProviders, setAvailableProviders] = useState({});
  const [tenantCalendars, setTenantCalendars] = useState({});
  const [selectedTenant, setSelectedTenant] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchProvidersData();
    if (tenants.length > 0) {
      setSelectedTenant(tenants[0].id);
    }
  }, [tenants, fetchProvidersData]);

  useEffect(() => {
    if (selectedTenant) {
      fetchTenantCalendars();
    }
  }, [selectedTenant, fetchTenantCalendars]);

  const fetchProvidersData = async () => {
    try {
      // Use first tenant to get providers list (same for all tenants)
      if (tenants.length > 0) {
        const response = await axios.get(`/api/v1/tenant/${tenants[0].id}/calendar/providers`);
        if (response.data.success) {
          setAvailableProviders(response.data.providers);
        }
      }
    } catch (error) {
      console.error('Failed to load providers:', error);
    }
  };

  const fetchTenantCalendars = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/v1/tenant/${selectedTenant}/calendar/settings`);
      if (response.data.success) {
        setTenantCalendars({
          ...tenantCalendars,
          [selectedTenant]: response.data.settings
        });
      }
    } catch (error) {
      setError('Failed to load tenant calendar settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSyncAll = async () => {
    try {
      setLoading(true);
      let totalSynced = 0;
      
      for (const tenant of tenants) {
        try {
          const response = await axios.post(`/api/v1/tenant/${tenant.id}/calendar/sync`);
          if (response.data.success) {
            totalSynced += response.data.synced_appointments || 0;
          }
        } catch (error) {
          console.error(`Failed to sync tenant ${tenant.id}:`, error);
        }
      }
      
      setSuccess(`Successfully synced ${totalSynced} appointments across all tenants`);
    } catch (error) {
      setError('Failed to sync calendars');
    } finally {
      setLoading(false);
    }
  };

  const selectedTenantData = tenants.find(t => t.id === selectedTenant);
  const currentCalendarSettings = tenantCalendars[selectedTenant] || { connected_calendars: [] };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800 font-display">Calendar Management</h2>
        <button
          onClick={handleSyncAll}
          disabled={loading}
          className="btn-primary"
        >
          {loading ? <LoadingSpinner size="small" /> : <Zap className="h-4 w-4" />}
          <span className="ml-2">Sync All Tenants</span>
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

      {/* Calendar Providers Overview */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 font-display">Available Calendar Providers</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(availableProviders).map(([key, provider]) => (
            <div key={key} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-gray-800">{provider.name}</h4>
                {key === 'curvehero' && <span className="badge badge-secondary">New!</span>}
              </div>
              <div className="space-y-2">
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
            </div>
          ))}
        </div>
      </div>

      {/* Tenant Selection */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 font-display">Tenant Calendar Settings</h3>
        <div className="mb-6">
          <label className="form-label">Select Tenant</label>
          <select
            value={selectedTenant}
            onChange={(e) => setSelectedTenant(e.target.value)}
            className="form-input max-w-md"
          >
            {tenants.map(tenant => (
              <option key={tenant.id} value={tenant.id}>
                {tenant.name} (ID: {tenant.id})
              </option>
            ))}
          </select>
        </div>

        {selectedTenantData && (
          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-medium text-gray-800">
                Calendar Connections for {selectedTenantData.name}
              </h4>
              <span className="badge badge-info">
                {currentCalendarSettings.connected_calendars.length} Connected
              </span>
            </div>

            {currentCalendarSettings.connected_calendars.length > 0 ? (
              <div className="space-y-3">
                {currentCalendarSettings.connected_calendars.map((calendar, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-primary-100 rounded-lg flex items-center justify-center">
                        <Calendar className="h-4 w-4 text-primary-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-800">{calendar.provider_name}</p>
                        <p className="text-xs text-gray-500">
                          Connected: {new Date(calendar.connected_at).toLocaleDateString()}
                        </p>
                        {calendar.features && (
                          <div className="flex space-x-1 mt-1">
                            {calendar.features.real_time_sync && 
                              <span className="badge badge-success text-xs">Real-time</span>}
                            {calendar.features.webhook_notifications && 
                              <span className="badge badge-info text-xs">Webhooks</span>}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="badge badge-success">Active</span>
                      <button
                        onClick={() => window.open(`/dashboard/calendar`, '_blank')}
                        className="text-primary-600 hover:text-primary-900"
                        title="Manage in Tenant Dashboard"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Calendar className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">No calendars connected for this tenant</p>
                <p className="text-sm text-gray-400 mt-1">
                  Tenants can connect calendars from their dashboard
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Calendar Integration Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Connections</p>
              <p className="text-3xl font-bold text-primary-600">
                {Object.values(tenantCalendars).reduce((acc, settings) => 
                  acc + (settings.connected_calendars?.length || 0), 0)}
              </p>
            </div>
            <Calendar className="h-8 w-8 text-primary-500" />
          </div>
        </div>
        
        <div className="stats-card-secondary">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Active Tenants</p>
              <p className="text-3xl font-bold text-secondary-700">
                {Object.values(tenantCalendars).filter(settings => 
                  settings.connected_calendars?.length > 0).length}
              </p>
            </div>
            <Building className="h-8 w-8 text-secondary-600" />
          </div>
        </div>

        <div className="stats-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Curve Hero</p>
              <p className="text-3xl font-bold text-primary-600">
                {Object.values(tenantCalendars).reduce((acc, settings) => 
                  acc + (settings.connected_calendars?.filter(c => c.provider === 'curvehero').length || 0), 0)}
              </p>
            </div>
            <Zap className="h-8 w-8 text-primary-500" />
          </div>
        </div>
      </div>
    </div>
  );
};

// Admin Settings Component
const AdminSettings = () => {
  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold text-gray-800 font-display">Admin Settings</h2>
      <div className="card p-8 text-center">
        <Settings className="h-16 w-16 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-800 mb-2">System Settings</h3>
        <p className="text-gray-600">Platform configuration and admin settings will be displayed here.</p>
      </div>
    </div>
  );
};

export default SuperAdminDashboard;