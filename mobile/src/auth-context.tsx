import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { setAuthToken, getAuthToken, api } from "./api";

const TOKEN_KEY = "drden_token";

type User = {
  user_id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  profile: any;
};

type AuthContextType = {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadStoredToken = useCallback(async () => {
    try {
      const stored = await AsyncStorage.getItem(TOKEN_KEY);
      if (stored) {
        setAuthToken(stored);
        setToken(stored);
        const me = await api.me();
        setUser({
          user_id: me.user_id,
          username: me.username,
          email: me.email,
          first_name: me.first_name || "",
          last_name: me.last_name || "",
          profile: me.profile,
        });
      } else {
        setUser(null);
        setToken(null);
      }
    } catch {
      setAuthToken(null);
      setToken(null);
      setUser(null);
      await AsyncStorage.removeItem(TOKEN_KEY);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStoredToken();
  }, [loadStoredToken]);

  const login = useCallback(async (username: string, password: string) => {
    const data = await api.login(username, password);
    setAuthToken(data.token);
    setToken(data.token);
    setUser({
      user_id: data.user_id,
      username: data.username,
      email: data.email || "",
      first_name: data.first_name || "",
      last_name: data.last_name || "",
      profile: data.profile,
    });
    await AsyncStorage.setItem(TOKEN_KEY, data.token);
  }, []);

  const logout = useCallback(async () => {
    setAuthToken(null);
    setToken(null);
    setUser(null);
    await AsyncStorage.removeItem(TOKEN_KEY);
  }, []);

  const register = useCallback(async (username: string, email: string, password: string) => {
    await api.register({ username, email, password });
    await login(username, password);
  }, [login]);

  const refreshUser = useCallback(async () => {
    if (!getAuthToken()) return;
    const me = await api.me();
    setUser({
      user_id: me.user_id,
      username: me.username,
      email: me.email,
      first_name: me.first_name || "",
      last_name: me.last_name || "",
      profile: me.profile,
    });
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, register, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
