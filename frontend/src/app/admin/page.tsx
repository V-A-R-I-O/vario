'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

// /admin lands on Intent management.
export default function AdminIndex() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/admin/intents');
  }, [router]);
  return null;
}
