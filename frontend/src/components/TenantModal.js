import React, { useState } from 'react';
import { Building, Mail, Phone, CreditCard } from 'lucide-react';
import LoadingSpinner from './LoadingSpinner';

const TenantModal = ({ isOpen, onClose, onSave, tenant = null }) => {
  const [formData, setFormData] = useState({
    name: tenant?.name || '',
    contact_email: tenant?.contact_email || '',
    phone: tenant?.phone || '',
    plan: tenant?.plan || 'basic'
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await onSave(formData);
      onClose();
      // Reset form
      setFormData({
        name: '',
        contact_email: '',
        phone: '',
        plan: 'basic'
      });
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to save tenant');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={onClose} />

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="sm:flex sm:items-start">
              <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-primary-100 sm:mx-0 sm:h-10 sm:w-10">
                <Building className="h-6 w-6 text-primary-600" />
              </div>
              <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left flex-1">
                <h3 className="text-lg leading-6 font-medium text-gray-900 font-display">
                  {tenant ? 'Edit Tenant' : 'Add New Tenant'}
                </h3>
                <div className="mt-4">
                  {error && (
                    <div className="mb-4 bg-red-50 border border-red-200 rounded-md p-3">
                      <div className="text-red-800 text-sm">{error}</div>
                    </div>
                  )}

                  <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Clinic Name */}
                    <div>
                      <label htmlFor="name" className="form-label">
                        Clinic Name
                      </label>
                      <div className="relative">
                        <input
                          id="name"
                          name="name"
                          type="text"
                          required
                          value={formData.name}
                          onChange={handleInputChange}
                          className="form-input pl-10"
                          placeholder="Enter clinic name"
                        />
                        <Building className="h-4 w-4 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                      </div>
                    </div>

                    {/* Contact Email */}
                    <div>
                      <label htmlFor="contact_email" className="form-label">
                        Contact Email
                      </label>
                      <div className="relative">
                        <input
                          id="contact_email"
                          name="contact_email"
                          type="email"
                          required
                          value={formData.contact_email}
                          onChange={handleInputChange}
                          className="form-input pl-10"
                          placeholder="admin@clinic.com"
                        />
                        <Mail className="h-4 w-4 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                      </div>
                    </div>

                    {/* Phone */}
                    <div>
                      <label htmlFor="phone" className="form-label">
                        Phone Number
                      </label>
                      <div className="relative">
                        <input
                          id="phone"
                          name="phone"
                          type="tel"
                          required
                          value={formData.phone}
                          onChange={handleInputChange}
                          className="form-input pl-10"
                          placeholder="+1 (555) 123-4567"
                        />
                        <Phone className="h-4 w-4 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                      </div>
                    </div>

                    {/* Plan Selection */}
                    <div>
                      <label htmlFor="plan" className="form-label">
                        Subscription Plan
                      </label>
                      <div className="relative">
                        <select
                          id="plan"
                          name="plan"
                          value={formData.plan}
                          onChange={handleInputChange}
                          className="form-input pl-10"
                        >
                          <option value="basic">Basic Plan - $49.99/month</option>
                          <option value="premium">Premium Plan - $99.99/month</option>
                        </select>
                        <CreditCard className="h-4 w-4 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                      </div>
                    </div>
                  </form>
                </div>
              </div>
            </div>
          </div>
          <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="btn-primary w-full sm:w-auto sm:ml-3 flex items-center justify-center"
            >
              {loading ? (
                <>
                  <LoadingSpinner size="small" />
                  <span className="ml-2">Saving...</span>
                </>
              ) : (
                <span>{tenant ? 'Update Tenant' : 'Create Tenant'}</span>
              )}
            </button>
            <button
              onClick={onClose}
              disabled={loading}
              className="btn-outline w-full sm:w-auto mt-3 sm:mt-0"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TenantModal;