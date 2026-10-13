'use client';

// Admin identity helpers for the admin console (slice-07). The admin role claim
// in the JWT maps to exactly one role pack; the console shows only that pack.
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken } from './auth';

export type AdminRole = 'hr_admin' | 'it_admin' | 'admissions_admin';

export interface AdminInfo {
  userId: string;
  email: string;
  role: AdminRole;
  pack: 'hr' | 'it' | 'admissions';
  badge: string; // short avatar/pill badge, e.g. "HR"
  label: string; // full role label, e.g. "HR Admin"
  name: string; // display name derived from email
}

const ADMIN_ROLE_META: Record<AdminRole, { pack: AdminInfo['pack']; badge: string; label: string }> = {
  hr_admin: { pack: 'hr', badge: 'HR', label: 'HR Admin' },
  it_admin: { pack: 'it', badge: 'IT', label: 'IT Admin' },
  admissions_admin: { pack: 'admissions', badge: 'AD', label: 'Admissions Admin' },
};

function nameFromEmail(email: string): string {
  const local = email.split('@')[0] || email;
  return local
    .split(/[._-]+/)
    .filter(Boolean)
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(' ');
}

// Decode the admin from the stored JWT. Returns null if there is no token or
// the role is not an admin role.
export function getAdminFromToken(): AdminInfo | null {
  const token = getToken();
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const role = payload.role as AdminRole;
    const meta = ADMIN_ROLE_META[role];
    if (!meta) return null;
    const email = payload.email || '';
    return {
      userId: payload.sub,
      email,
      role,
      pack: meta.pack,
      badge: meta.badge,
      label: meta.label,
      name: email ? nameFromEmail(email) : meta.label,
    };
  } catch {
    return null;
  }
}

// Client hook: resolves the admin after mount and redirects non-admins away.
// `status` is 'loading' until mounted, then 'admin' or 'denied'.
export function useAdmin() {
  const router = useRouter();
  const [admin, setAdmin] = useState<AdminInfo | null>(null);
  const [status, setStatus] = useState<'loading' | 'admin' | 'denied'>('loading');

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setStatus('denied');
      router.push('/login');
      return;
    }
    const info = getAdminFromToken();
    if (!info) {
      // Authenticated but not an admin — send to the end-user app.
      setStatus('denied');
      router.push('/home');
      return;
    }
    setAdmin(info);
    setStatus('admin');
  }, [router]);

  return { admin, status };
}
