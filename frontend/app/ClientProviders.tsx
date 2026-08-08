'use client';

import { AuthProvider } from "@/shared/auth/AuthContext";
import { WorkspaceProvider } from "@/shared/context/WorkspaceContext";

export default function ClientProviders({ children }: { children: React.ReactNode }) {
  return <AuthProvider><WorkspaceProvider>{children}</WorkspaceProvider></AuthProvider>;
}
