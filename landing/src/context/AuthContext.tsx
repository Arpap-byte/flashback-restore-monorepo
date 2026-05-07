"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://148.230.116.52:8000";

export interface User {
  id: string;
  email: string;
  essais_restants: number;
  est_abonne: boolean;
  credits: number;
}

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore session from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("flashback_auth");
    if (stored) {
      try {
        const { token: t, user: u } = JSON.parse(stored);
        setToken(t);
        setUser(u);
      } catch {
        localStorage.removeItem("flashback_auth");
      }
    }
    setLoading(false);
  }, []);

  const saveAuth = useCallback((t: string, u: User) => {
    setToken(t);
    setUser(u);
    localStorage.setItem("flashback_auth", JSON.stringify({ token: t, user: u }));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Identifiants incorrects.");
    }
    const data = await res.json();
    saveAuth(data.token, data.utilisateur);
  }, [saveAuth]);

  const register = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Erreur lors de l'inscription.");
    }
    const data = await res.json();
    saveAuth(data.token, data.utilisateur);
  }, [saveAuth]);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("flashback_auth");
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

/** Get stored token for API calls outside React */
export function getStoredToken(): string | null {
  try {
    const stored = localStorage.getItem("flashback_auth");
    if (stored) {
      return JSON.parse(stored).token;
    }
  } catch {}
  return null;
}
