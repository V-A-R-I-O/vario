'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { getToken, clearToken } from '@/lib/auth';
import { fetchConversations } from '@/lib/api';
import { onConversationsChanged } from '@/lib/conversationEvents';

export default function HomeLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [conversations, setConversations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRailOpen, setIsRailOpen] = useState(false);
  const [user, setUser] = useState<any>(null); // To decode from JWT if needed

  const loadConversations = useCallback(() => {
    fetchConversations()
      .then(res => {
        if (res.status === 'success') {
          setConversations(res.data.conversations);
        }
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setMounted(true);
    const token = getToken();
    if (!token) {
      router.push('/login');
      return;
    }

    try {
      // Very basic JWT decode for user info
      const payload = JSON.parse(atob(token.split('.')[1]));
      setUser(payload);
    } catch(e) {}

    loadConversations();
    // Reload when a conversation is created or gets a new message.
    return onConversationsChanged(loadConversations);
  }, [router, loadConversations]);

  if (!mounted) return null;

  const isAdmin = typeof user?.role === 'string' && user.role.endsWith('_admin');

  const handleLogout = () => {
    clearToken();
    router.push('/login');
  };

  const getRoleBadgeClass = (role: string) => {
    switch(role) {
      case 'hr': return 'role-hr';
      case 'it': return 'role-it';
      case 'admissions': return 'role-adm';
      default: return '';
    }
  };

  const getRoleBadgeLabel = (role: string) => {
    switch(role) {
      case 'hr': return 'HR';
      case 'it': return 'IT';
      case 'admissions': return 'AD';
      default: return role.toUpperCase();
    }
  };
  
  const formatTime = (ts: string) => {
    // simplified time format
    const d = new Date(ts);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="shell">
      <aside className={`rail ${isRailOpen ? 'open' : ''}`}>
        <div className="rail-brand">
          <div className="mark"></div>
          <div className="word">VARIO</div>
        </div>
        <button className="rail-cta" onClick={() => router.push('/home/new')}>
          <svg viewBox="0 0 24 24" fill="none" style={{width: '14px', height: '14px'}}>
            <path d="M12 5v14M5 12h14" stroke="#0D2622" strokeWidth="2.2" strokeLinecap="round"/>
          </svg>
          New conversation
        </button>
        {isAdmin && (
          <nav className="rail-nav" aria-label="Admin">
            <Link href="/admin">
              <svg viewBox="0 0 24 24" fill="none">
                <path d="M12 3 4 6v6c0 4.5 3.4 8.3 8 9 4.6-.7 8-4.5 8-9V6l-8-3Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/>
              </svg>
              Admin console
            </Link>
          </nav>
        )}
        <div className="rail-section-label">Conversations</div>
        
        <div className="rail-scroll">
          {loading ? (
             <div className="conv-item">
               <div className="skeleton" style={{width: '32px', height: '32px', borderRadius: '8px'}} />
               <div className="conv-meta" style={{gap: '8px'}}>
                 <div className="skeleton skel-line" style={{width: '80%'}} />
                 <div className="skeleton skel-line" style={{width: '60%'}} />
               </div>
             </div>
          ) : conversations.length === 0 ? (
             <div style={{padding: '20px', fontSize: '13px', color: 'var(--text-muted)'}}>No conversations yet.</div>
          ) : (
            conversations.map(conv => (
              <div key={conv.id} className={`conv-item ${getRoleBadgeClass(conv.role_pack)}`} onClick={() => router.push(`/home/chat/${conv.id}`)}>
                <div className="conv-badge">{getRoleBadgeLabel(conv.role_pack)}</div>
                <div className="conv-meta">
                  <div className="conv-title">{conv.title || `New ${getRoleBadgeLabel(conv.role_pack)} conversation`}</div>
                  <div className="conv-preview">{conv.last_message_preview || 'New conversation'}</div>
                </div>
                <div className="conv-time">{formatTime(conv.last_message_at)}</div>
              </div>
            ))
          )}
        </div>
        
        <div className="rail-user">
          <div className="avatar">{user?.email?.substring(0,2).toUpperCase() || 'U'}</div>
          <div>
            <div className="name">{user?.email || 'User'}</div>
            <div className="role">{user?.role || 'Employee'}</div>
          </div>
          <button className="logout" onClick={handleLogout} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '8px' }} title="Log out">
            <svg viewBox="0 0 24 24" fill="none" style={{width: '18px', height: '18px'}}>
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </aside>
      
      <div className="rail-scrim" onClick={() => setIsRailOpen(false)}></div>
      
      {children}
    </div>
  );
}
