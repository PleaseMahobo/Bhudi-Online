"use client";

import { createContext, useContext, useEffect, useRef, useState, ReactNode } from "react";
import { getCurrentUser } from "@/lib/api";
import { getSupabaseBrowserClient } from "@/lib/supabase-browser";

type User = { id: string; email: string; firstName: string; lastName: string; role: string; active: boolean; tenant_id: string | null; mfa_enabled: boolean };
type AuthContextType = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string, mfaCode?: string) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};
const AuthContext = createContext<AuthContextType | null>(null);

function normalizeUser(data: any): User | null {
  const value = data?.user ?? data;
  if (!value) return null;
  return {
    id: String(value.id ?? ""),
    email: String(value.email ?? ""),
    firstName: String(value.first_name ?? value.firstName ?? ""),
    lastName: String(value.last_name ?? value.lastName ?? ""),
    role: String(value.role ?? ""),
    active: Boolean(value.active ?? true),
    tenant_id: value.tenant_id ? String(value.tenant_id) : null,
    mfa_enabled: Boolean(value.mfa_enabled ?? value.mfaEnabled ?? false),
  };
}

async function clearSupabaseSession(): Promise<void> {
  await fetch("/api/auth/supabase-session", {
    method: "DELETE",
    credentials: "include",
    cache: "no-store",
  }).catch(() => undefined);
}

async function authenticateBhudiLogin(supabase: ReturnType<typeof getSupabaseBrowserClient>, mfaCode?: string): Promise<void> {
  // Always obtain the current Supabase session immediately before promotion.
  // Supabase auto-refreshes browser sessions, so the token captured at
  // password entry can become stale while the user is completing MFA.
  const { data, error } = await supabase.auth.getSession();
  if (error || !data.session?.access_token) {
    throw new Error("Supabase session unavailable");
  }

  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "Authorization": `Bearer ${data.session.access_token}`,
    },
    body: JSON.stringify(mfaCode ? { mfa_code: mfaCode } : {}),
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(typeof detail === "string" ? detail : "Authentication failed");
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const loginInProgress = useRef(false);

  async function refreshUser(): Promise<void> {
    try {
      const current = await getCurrentUser();
      setUser(normalizeUser(current));
    } catch (error) {
      setUser(null);
      throw error;
    }
  }

  async function login(email: string, password: string, mfaCode?: string): Promise<boolean> {
    const supabase = getSupabaseBrowserClient();
    loginInProgress.current = true;
    try {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw new Error(error.message);
      if (!data.session?.access_token) throw new Error("Supabase authentication succeeded but no session was returned");

      try {
        await authenticateBhudiLogin(supabase, mfaCode);
      } catch (error) {
        const message = String((error as Error)?.message || "");
        // Keep the verified Supabase session alive while the user completes
        // the required MFA challenge. It is promoted to a Bhudi session only
        // after the correct 6-digit code is supplied.
        if (message === "mfa_required" || message === "Invalid authenticator code") {
          throw error;
        }
        await clearSupabaseSession();
        await supabase.auth.signOut();
        throw error;
      }

      const current = normalizeUser(await getCurrentUser());
      if (!current) throw new Error("Unable to resolve Bhudi user after authentication");
      setUser(current);
      return true;
    } finally {
      loginInProgress.current = false;
    }
  }

  async function logout(): Promise<void> {
    loginInProgress.current = false;
    try {
      await clearSupabaseSession();
      await getSupabaseBrowserClient().auth.signOut();
      await fetch("/api/auth/logout", { method: "POST", credentials: "include", cache: "no-store" }).catch(() => undefined);
    } finally {
      setUser(null);
    }
  }

  useEffect(() => {
    let active = true;
    const supabase = getSupabaseBrowserClient();
    const { data: listener } = supabase.auth.onAuthStateChange(async (_event) => {
      if (!active || loginInProgress.current) return;
      try {
        await refreshUser();
      } catch {
        if (active) setUser(null);
      }
      if (active) setLoading(false);
    });

    refreshUser().catch(() => undefined).finally(() => {
      if (active) setLoading(false);
    });

    return () => {
      active = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  return <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
