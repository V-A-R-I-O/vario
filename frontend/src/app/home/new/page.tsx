'use client';

import { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createConversation } from '@/lib/api';
import { notifyConversationsChanged } from '@/lib/conversationEvents';

export default function NewConversationPage() {
  const router = useRouter();
  const [creating, setCreating] = useState(false);
  // A ref too: a double-click must not create two conversations.
  const creatingRef = useRef(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (role_pack: string) => {
    if (creatingRef.current) return;
    creatingRef.current = true;
    setCreating(true);
    setError(null);
    try {
      const res = await createConversation(role_pack);
      if (res.status === 'success') {
        notifyConversationsChanged();
        router.push(`/home/chat/${res.data.id}`);
        return;
      }
      setError("Couldn't start the conversation. Please try again.");
    } catch (e) {
      console.error('Failed to create conversation', e);
      setError("Couldn't start the conversation. Please try again.");
    } finally {
      creatingRef.current = false;
      setCreating(false);
    }
  };

  return (
    <main className="canvas">
      <div className="topbar">
        <button className="rail-toggle" onClick={() => document.querySelector('.rail')?.classList.toggle('open')}>
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </button>
        <h1>New conversation</h1>
      </div>
      <div className="content-scroll">
        <div className="content-pad" style={{maxWidth: '900px'}}>
          <p style={{color: 'var(--text-muted)', fontSize: '14px', marginBottom: '26px', maxWidth: '520px'}}>
            Choose which department you&apos;d like to talk to. You can switch anytime by starting another conversation.
          </p>

          {error && (
            <div className="banner banner-danger" role="alert" style={{ marginBottom: '18px' }}>
              {error}
            </div>
          )}

          <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px'}}>

            <button className="panel role-hr" style={{textAlign: 'left', padding: '0', borderLeft: '3px solid var(--role)', cursor: 'pointer'}} disabled={creating} onClick={() => handleCreate('hr')}>
              <div style={{padding: '22px 20px'}}>
                <div style={{width: '38px', height: '38px', borderRadius: '9px', background: 'var(--role-tint)', color: 'var(--role-dark)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '12.5px', marginBottom: '16px'}}>HR</div>
                <h3 style={{fontSize: '15.5px', marginBottom: '6px'}}>HR</h3>
                <p style={{fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '18px'}}>Leave balance, leave requests, and HR policy questions.</p>
                <span style={{fontSize: '12.5px', fontWeight: 700, color: 'var(--role-dark)'}}>Start conversation &rarr;</span>
              </div>
            </button>

            <button className="panel role-it" style={{textAlign: 'left', padding: '0', borderLeft: '3px solid var(--role)', cursor: 'pointer'}} disabled={creating} onClick={() => handleCreate('it')}>
              <div style={{padding: '22px 20px'}}>
                <div style={{width: '38px', height: '38px', borderRadius: '9px', background: 'var(--role-tint)', color: 'var(--role-dark)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '12.5px', marginBottom: '16px'}}>IT</div>
                <h3 style={{fontSize: '15.5px', marginBottom: '6px'}}>IT Support</h3>
                <p style={{fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '18px'}}>IT tickets, ticket status, and password resets.</p>
                <span style={{fontSize: '12.5px', fontWeight: 700, color: 'var(--role-dark)'}}>Start conversation &rarr;</span>
              </div>
            </button>

            <button className="panel role-adm" style={{textAlign: 'left', padding: '0', borderLeft: '3px solid var(--role)', cursor: 'pointer'}} disabled={creating} onClick={() => handleCreate('admissions')}>
              <div style={{padding: '22px 20px'}}>
                <div style={{width: '38px', height: '38px', borderRadius: '9px', background: 'var(--role-tint)', color: 'var(--role-dark)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '12.5px', marginBottom: '16px'}}>AD</div>
                <h3 style={{fontSize: '15.5px', marginBottom: '6px'}}>Admissions</h3>
                <p style={{fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '18px'}}>Application status, document checklists, and fee deadlines.</p>
                <span style={{fontSize: '12.5px', fontWeight: 700, color: 'var(--role-dark)'}}>Start conversation &rarr;</span>
              </div>
            </button>

          </div>
        </div>
      </div>
    </main>
  );
}
