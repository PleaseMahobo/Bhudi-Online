"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { getCurrentUser } from "@/lib/api";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser";

type User = { id: string; email: string; firstName: string; lastName: string; role: string; active: boolean };
type AuthContextType = { user: User | null; loading: boolean; login: (email: string, password: string, mfaCode?: string) => Promise<boolean>; logout: () => Promise<void>; refreshUser: () => Promise<void> };
const AuthContext = createContext<AuthContextType | null>(null);

function normalizeUser(data: any): User | null {
  const value = data?.user ?? data;
  if (!value) return null;
  return { id: String(value.id ?? ""), email: String(value.email ?? ""), firstName: String(value.first_name ?? value.firstName ?? ""), lastName: String(value.last_name ?? value.lastName ?? ""), role: String(value.role ?? ""), active: Boolean(value.active ?? true) };
}

async function syncSupabaseSession(accessToken: string) {
  const response = await fetch("/api/auth/supabase-session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ access_token: accessToken }),
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Unable to establish Bhudi session");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function refreshUser() {
    try {
      const current = await getCurrentUser();
      const normalized = normalizeUser(current);
      setUser(normalized);
      return normalized;
    } catch (error) {
      setUser(null);
      throw error;
    }
  }

  async function login(email: string, password: string, _mfaCode?: string): Promise<boolean> {
    const supabase = getSupabaseBrowserClient();
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw new Error(error.message);
    if (!data.session?.access_token) throw new Error("Supabase did not return an authentication session");

    await syncSupabaseSession(data.session.access_token);
    const current = await refreshUser();
    return Boolean(current);
  }

  async function logout() {
    try {
      await fetch("/api/auth/supabase-session", { method: "DELETE", credentials: "include", cache: "no-store" });
      await getSupabaseBrowserClient().auth.signOut();
    } finally {
      setUser(null);
    }
  }

  useEffect(() => {
    let active = true;
    const supabase = getSupabaseBrowserClient();
    const { data: listener } = supabase.auth.onAuthStateChange(async (_event, session) => {
      if (!active) return;
      if (session?.access_token) {
        try { await syncSupabaseSession(session.access_token); await refreshUser(); }
        catch { setUser(null); }
      } else {
        setUser(null);
      }
      setLoading(false);
    });

    refreshUser().catch(() => undefined).finally(() => { if (active) setLoading(false); });
    return () => { active = false; listener.subscription.unsubscribe(); };
  }, []);

  return <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
