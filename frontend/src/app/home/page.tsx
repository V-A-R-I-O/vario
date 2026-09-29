'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, clearToken } from '@/lib/auth';

export default function HomePage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const token = getToken();
    if (!token) {
      router.push('/login');
    }
  }, [router]);

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white shadow-sm px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold text-gray-900">V.A.R.I.O.</h1>
        <button 
          onClick={() => {
            clearToken();
            router.push('/login');
          }}
          className="text-gray-600 hover:text-gray-900"
        >
          Sign out
        </button>
      </header>
      <main className="flex-1 p-6 flex items-center justify-center">
        <div className="text-center text-gray-500">
          <p className="mb-2 text-lg">Welcome to V.A.R.I.O.</p>
          <p className="text-sm">Start your first conversation.</p>
        </div>
      </main>
    </div>
  );
}
