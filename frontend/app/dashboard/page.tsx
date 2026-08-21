'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ContextAwareDashboard from '@/shared/components/ContextAwareDashboard';
import { useAuth } from '@/shared/auth/AuthContext';

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">
        Verifying authentication…
      </div>
    );
  }

  return <ContextAwareDashboard />;
}
