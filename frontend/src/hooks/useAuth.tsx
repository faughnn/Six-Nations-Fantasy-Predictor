import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import api from '../api/client';
import { authApi, type AuthUser } from '../api/auth';

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string) => Promise<void>;
  googleLogin: (credential: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const TOKEN_KEY = 'auth_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const setToken = (token: string) => {
    localStorage.setItem(TOKEN_KEY, token);
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  };

  const clearToken = () => {
    localStorage.removeItem(TOKEN_KEY);
    delete api.defaults.headers.common['Authorization'];
  };

  // On mount, check for existing token
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      authApi
        .getMe()
        .then(setUser)
        .catch(() => clearToken())
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    setToken(res.token);
    setUser(res.user);
  }, []);

  const register = useCallback(async (email: string, name: string, password: string) => {
    const res = await authApi.register(email, name, password);
    setToken(res.token);
    setUser(res.user);
  }, []);

  const googleLogin = useCallback(async (credential: string) => {
    const res = await authApi.googleAuth(credential);
    setToken(res.token);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, googleLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
