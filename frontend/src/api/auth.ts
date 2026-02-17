import api from './client';

export interface AuthUser {
  id: number;
  email: string;
  name: string;
  avatar_url: string | null;
}

export interface AuthResponse {
  token: string;
  user: AuthUser;
}

export const authApi = {
  register: async (email: string, name: string, password: string): Promise<AuthResponse> => {
    const response = await api.post('/api/auth/register', { email, name, password });
    return response.data;
  },

  login: async (email: string, password: string): Promise<AuthResponse> => {
    const response = await api.post('/api/auth/login', { email, password });
    return response.data;
  },

  googleAuth: async (credential: string): Promise<AuthResponse> => {
    const response = await api.post('/api/auth/google', { credential });
    return response.data;
  },

  getMe: async (): Promise<AuthUser> => {
    const response = await api.get('/api/auth/me');
    return response.data;
  },
};
