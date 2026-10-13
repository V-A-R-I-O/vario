'use client';

// Shared admin top bar: page title + role badge (HR/IT/Admissions Admin) +
// admin name + logout. The role badge reflects the admin's own pack only.
import { useRouter } from 'next/navigation';
import { clearToken } from '@/lib/auth';
import type { AdminInfo } from '@/lib/adminAuth';

export function AdminTopbar({ title, admin }: { title: string; admin: AdminInfo | null }) {
  const router = useRouter();

  const handleLogout = () => {
    clearToken();
    router.push('/login');
  };

  const initials = (admin?.name || admin?.email || 'A').slice(0, 2).toUpperCase();

  return (
    <div className="topbar">
      <button
        className="rail-toggle"
        onClick={() => document.querySelector('.rail')?.classList.toggle('open')}
        aria-label="Toggle sidebar"
      >
        <svg viewBox="0 0 24 24" fill="none">
          <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>
      <h1>{title}</h1>
      <div className="spacer" style={{ flex: 1 }} />
      {admin && (
        <>
          <span className="pill" style={{ marginRight: 12 }}>
            <span className="dot" />
            {admin.label}
          </span>
          <div
            className="avatar"
            style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: 'var(--line)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 11,
              fontWeight: 700,
              color: 'var(--text-muted)',
            }}
          >
            {initials}
          </div>
          <span style={{ fontSize: 13, fontWeight: 700, margin: '0 10px 0 8px' }}>{admin.name}</span>
        </>
      )}
      <button className="btn btn-ghost btn-sm" type="button" onClick={handleLogout}>
        Log out
      </button>
    </div>
  );
}
