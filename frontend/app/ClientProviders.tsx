'use client';

import { AuthProvider } from "@/shared/auth/AuthContext";

export default function ClientProviders({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthProvider>{children}</AuthProvider>
}