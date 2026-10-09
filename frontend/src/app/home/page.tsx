'use client';

import { useRouter } from 'next/navigation';

export default function HomePage() {
  const router = useRouter();

  return (
    <main className="canvas">
      <div className="topbar">
        <button className="rail-toggle" onClick={() => document.querySelector('.rail')?.classList.toggle('open')}>
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </button>
        <h1>Conversations</h1>
        <div className="spacer"></div>
        <button className="btn btn-signal" onClick={() => router.push('/home/new')}>
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"/>
          </svg>
          New conversation
        </button>
      </div>
      <div className="content-scroll">
        <div className="empty-state" style={{paddingTop: '110px'}}>
          <div className="icon">
            <svg viewBox="0 0 24 24" fill="none" style={{width: '24px', height: '24px', color: 'var(--text-faint)'}}>
              <path d="M4 12h2.2l1.8-5.4 3 11 2.6-8.6 1.6 4.6h2.4l1.6-3 1.4 1.4h2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <h3>Pick a conversation</h3>
          <p>Select a conversation from the left, or start a new one with HR, IT Support, or Admissions.</p>
        </div>
      </div>
    </main>
  );
}
