import axios, { AxiosInstance } from 'axios';

// API base URL from environment
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth token
apiClient.interceptors.request.use(
  async (config) => {
    // Get token from MSAL if available
    const token = localStorage.getItem('msal.idtoken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

// Chat API
export const chatApi = {
  sendMessage: async (payload: {
    query: string;
    conversationId?: string;
    userId?: string;
  }) => {
    const response = await apiClient.post('/chat', payload);
    return response.data;
  },

  getConversation: async (conversationId: string) => {
    const response = await apiClient.get(`/conversations/${conversationId}`);
    return response.data;
  },

  listConversations: async () => {
    const response = await apiClient.get('/conversations');
    return response.data;
  },
};

// Documents API
export const documentsApi = {
  upload: async (file: File, metadata?: Record<string, string>) => {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    const response = await apiClient.post('/documents', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getDocument: async (documentId: string) => {
    const response = await apiClient.get(`/documents/${documentId}`);
    return response.data;
  },

  listDocuments: async (filters?: Record<string, string>) => {
    const response = await apiClient.get('/documents', { params: filters });
    return response.data;
  },

  deleteDocument: async (documentId: string) => {
    const response = await apiClient.delete(`/documents/${documentId}`);
    return response.data;
  },
};

// Search API
export const searchApi = {
  search: async (payload: {
    query: string;
    filters?: Record<string, string>;
    topK?: number;
    searchType?: 'hybrid' | 'vector' | 'keyword';
  }) => {
    const response = await apiClient.post('/search', payload);
    return response.data;
  },
};

// Health check
export const healthApi = {
  check: async () => {
    const response = await apiClient.get('/health');
    return response.data;
  },
};

export default apiClient;
