"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { login as apiLogin, logout as apiLogout, getCurrentUser, refreshAccessToken } from "@/lib/api";

type User = { id: string; email: string; firstName: string; lastName: string; role: string; active: boolean };
type AuthContextType = { user: User | null; loading: boolean; login: (email: string, password: string, mfaCode?: string) => Promise<boolean>; logout: () => Promise<void>; refreshUser: () => Promise<void> };
const AuthContext = createContext<AuthContextType | null>(null);

function normalizeUser(data: any): User | null {
  const value = data?.user ?? data;
  if (!value) return null;
  return { id: String(value.id ?? ""), email: String(value.email ?? ""), firstName: String(value.first_name ?? value.firstName ?? ""), lastName: String(value.last_name ?? value.lastName ?? ""), role: String(value.role ?? ""), active: Boolean(value.active ?? true) };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function refreshUser() {
    try {
      let current: any;
      try { current = await getCurrentUser(); }
      catch (error: any) {
        if (String(error?.message ?? "").toLowerCase().includes("401")) {
          await refreshAccessToken();
          current = await getCurrentUser();
        } else throw error;
      }
      setUser(normalizeUser(current));
    } catch (error) {
      setUser(null);
      console.error("Failed to refresh user:", error);
    }
  }

  async function login(email: string, password: string, mfaCode?: string): Promise<boolean> {
    try {
      const response = await apiLogin(email, password, mfaCode);
      const loggedInUser = normalizeUser(response);
      if (loggedInUser) { setUser(loggedInUser); return true; }
      await refreshUser();
      return true;
    } catch (error) {
      console.error("Login failed:", error);
      return false;
    }
  }

  async function logout() {
    try { await apiLogout(); }
    catch (error) { console.error("Logout error:", error); }
    finally { setUser(null); }
  }

  useEffect(() => { refreshUser().finally(() => setLoading(false)); }, []);

  return <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
