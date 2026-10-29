'use client';

// Admin console shell (slice-07): side rail + role-scoped nav. Distinct from
// the end-user shell. Non-admins are redirected away by useAdmin().
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAdmin } from '@/lib/adminAuth';

const NAV = [
  {
    href: '/admin/intents',
    label: 'Intent management',
    icon: <path d="M4 6h16M4 12h16M4 18h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />,
  },
  {
    href: '/admin/audit-log',
    label: 'Audit log',
    icon: (
      <path
        d="M9 3h6l1 3h3v2H5V6h3l1-3ZM6 8h12l-1 12a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L6 8Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    ),
  },
  {
    href: '/admin/conversation-logs',
    label: 'Conversation logs',
    icon: <path d="M4 5h16v11H8l-4 4V5Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />,
  },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { status } = useAdmin();

  // Avoid flashing the console to a non-admin while the redirect runs.
  if (status !== 'admin') return null;

  return (
    <div className="shell">
      <aside className="rail">
        <div className="rail-brand">
          <div className="mark" />
          <div>
            <div className="word">VARIO</div>
            <div className="sub">Admin console</div>
          </div>
        </div>
        <nav className="rail-nav">
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link key={item.href} href={item.href} className={active ? 'active' : undefined}>
                <svg viewBox="0 0 24 24" fill="none">
                  {item.icon}
                </svg>
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="rail-scrim" onClick={() => document.querySelector('.rail')?.classList.remove('open')} />
      {children}
    </div>
  );
}
