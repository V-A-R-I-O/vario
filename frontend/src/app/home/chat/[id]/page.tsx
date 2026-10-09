'use client';

export default function ChatStubPage({ params }: { params: { id: string } }) {
  return (
    <main className="canvas">
      <div className="topbar">
        <button className="rail-toggle" onClick={() => document.querySelector('.rail')?.classList.toggle('open')}>
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </button>
        <h1>Chat View (Stub)</h1>
      </div>
      <div className="content-scroll">
        <div className="content-pad">
          <p>This is a stub for the chat view. Conversation ID: {params.id}</p>
        </div>
      </div>
    </main>
  );
}
