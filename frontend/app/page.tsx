// frontend/app/page.tsx
'use client';

import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center">
      <div className="text-center max-w-4xl mx-auto px-6">
        <h1 className="text-6xl font-bold mb-6">Bhudi RMM</h1>
        <p className="text-2xl text-zinc-400 mb-10">
          Remote Monitoring & Management Platform
        </p>
        
        <div className="space-x-4">
          <Link 
            href="/dashboard" 
            className="bg-white text-black px-8 py-4 rounded-xl font-semibold hover:bg-zinc-200 transition"
          >
            Go to Dashboard
          </Link>
          <a 
            href="https://bhudi-online-production.up.railway.app/docs" 
            target="_blank"
            className="border border-white px-8 py-4 rounded-xl font-semibold hover:bg-white/10 transition"
          >
            View API Docs
          </a>
        </div>
      </div>
    </div>
  );
}
  );
}
