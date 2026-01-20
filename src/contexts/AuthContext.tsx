import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { toast } from '@/hooks/use-toast';

interface User {
  id: string;
  email: string;
  name?: string;
  createdAt: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, name?: string) => Promise<void>;
  signOut: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const STORAGE_KEY = 'cleo_auth_token';
const USER_STORAGE_KEY = 'cleo_user';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for stored auth on mount
    const token = localStorage.getItem(STORAGE_KEY);
    const storedUser = localStorage.getItem(USER_STORAGE_KEY);
    
    if (token && storedUser) {
      try {
        const userData = JSON.parse(storedUser);
        setUser(userData);
        
        // Verify token is still valid
        verifyToken(token).catch(() => {
          // Token invalid, clear auth
          localStorage.removeItem(STORAGE_KEY);
          localStorage.removeItem(USER_STORAGE_KEY);
          setUser(null);
        });
      } catch (error) {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem(USER_STORAGE_KEY);
      }
    }
    
    setLoading(false);
  }, []);

  const verifyToken = async (token: string): Promise<boolean> => {
    try {
      // In a real app, this would verify with the backend
      // For now, we'll just check if the token exists
      return !!token;
    } catch {
      return false;
    }
  };

  const signIn = async (email: string, password: string) => {
    try {
      setLoading(true);
      
      // Try to sign in via API
      const response = await signInWithAPI(email, password);
      
      if (response) {
        // Store token and user data
        localStorage.setItem(STORAGE_KEY, response.token);
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(response.user));
        setUser(response.user);
        
        toast({
          title: 'Signed in successfully',
          description: `Welcome back, ${response.user.name || response.user.email}!`,
        });
      } else {
        throw new Error('Invalid credentials');
      }
    } catch (error: any) {
      // Fallback to mock authentication for development
      console.warn('API sign in failed, using mock auth:', error.message);
      
      // Mock authentication (remove in production)
      if (email && password) {
        const mockUser: User = {
          id: '1',
          email,
          name: email.split('@')[0],
          createdAt: new Date().toISOString(),
        };
        
        const mockToken = `mock_token_${Date.now()}`;
        localStorage.setItem(STORAGE_KEY, mockToken);
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(mockUser));
        setUser(mockUser);
        
        toast({
          title: 'Signed in successfully',
          description: `Welcome back, ${mockUser.name || mockUser.email}!`,
        });
      } else {
        throw new Error('Email and password are required');
      }
    } finally {
      setLoading(false);
    }
  };

  const signUp = async (email: string, password: string, name?: string) => {
    try {
      setLoading(true);
      
      // Try to sign up via API
      const response = await signUpWithAPI(email, password, name);
      
      if (response) {
        // Store token and user data
        localStorage.setItem(STORAGE_KEY, response.token);
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(response.user));
        setUser(response.user);
        
        toast({
          title: 'Account created successfully',
          description: `Welcome, ${response.user.name || response.user.email}!`,
        });
      } else {
        throw new Error('Failed to create account');
      }
    } catch (error: any) {
      // Fallback to mock registration for development
      console.warn('API sign up failed, using mock auth:', error.message);
      
      // Mock registration (remove in production)
      if (email && password) {
        const mockUser: User = {
          id: Date.now().toString(),
          email,
          name: name || email.split('@')[0],
          createdAt: new Date().toISOString(),
        };
        
        const mockToken = `mock_token_${Date.now()}`;
        localStorage.setItem(STORAGE_KEY, mockToken);
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(mockUser));
        setUser(mockUser);
        
        toast({
          title: 'Account created successfully',
          description: `Welcome, ${mockUser.name || mockUser.email}!`,
        });
      } else {
        throw new Error('Email and password are required');
      }
    } finally {
      setLoading(false);
    }
  };

  const signOut = () => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
    setUser(null);
    
    toast({
      title: 'Signed out',
      description: 'You have been signed out successfully.',
    });
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        signIn,
        signUp,
        signOut,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// API functions (will be connected to backend)
async function signInWithAPI(
  email: string,
  password: string
): Promise<{ token: string; user: User } | null> {
  try {
    // This will be implemented when backend auth is ready
    // Import signIn from api and use it:
    // import { signIn as signInAPI } from '@/lib/api';
    // const response = await signInAPI({ email, password });
    // return response;
    return null; // Return null to trigger fallback
  } catch {
    return null;
  }
}

async function signUpWithAPI(
  email: string,
  password: string,
  name?: string
): Promise<{ token: string; user: User } | null> {
  try {
    // This will be implemented when backend auth is ready
    // Import signUp from api and use it:
    // import { signUp as signUpAPI } from '@/lib/api';
    // const response = await signUpAPI({ email, password, name });
    // return response;
    return null; // Return null to trigger fallback
  } catch {
    return null;
  }
}
