import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_URL } from '../config/constants';

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  async (config) => {
    const token = await AsyncStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      await AsyncStorage.removeItem('token');
      await AsyncStorage.removeItem('user');
    }
    return Promise.reject(error);
  }
);

// Auth APIs
export const auth = {
  login: (email, password) =>
    api.post('/auth/login', { email, password }),

  register: (data) =>
    api.post('/auth/register', data),

  logout: () =>
    api.post('/auth/logout'),
};

// Inventory APIs
export const inventory = {
  getAll: (params) =>
    api.get('/inventory', { params }),

  getById: (id) =>
    api.get(`/inventory/${id}`),

  create: (data) =>
    api.post('/inventory', data),

  update: (id, data) =>
    api.patch(`/inventory/${id}`, data),

  delete: (id) =>
    api.delete(`/inventory/${id}`),
};

// Sales APIs
export const sales = {
  create: (data) =>
    api.post('/sales', data),

  getAll: (params) =>
    api.get('/sales', { params }),

  getById: (id) =>
    api.get(`/sales/${id}`),
};

// Analytics APIs
export const analytics = {
  getDashboard: () =>
    api.get('/analytics/dashboard'),

  getSalesData: (params) =>
    api.get('/analytics/sales', { params }),
};

// Billing APIs
export const billing = {
  getPricingTiers: () =>
    api.get('/billing/pricing-tiers'),

  getGMVStats: () =>
    api.get('/billing/gmv-stats'),

  calculateCost: (tier, gmv) =>
    api.post('/billing/calculate-cost', { tier, gmv }),
};

// Diagnostics APIs
export const diagnostics = {
  getHealth: () =>
    api.get('/diagnostics/health'),

  getRecentEvents: (params) =>
    api.get('/diagnostics/recent-events', { params }),

  generateReport: () =>
    api.post('/diagnostics/generate-report'),

  createTicket: (data) =>
    api.post('/diagnostics/support-ticket', data),
};

export default api;
