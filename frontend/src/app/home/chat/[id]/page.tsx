'use client';

import { useEffect, useRef, useState } from 'react';
import { fetchMessages, sendChatMessage, fetchConversations } from '@/lib/api';
import { BotMessage, UserMessage, type BotMessageData } from '@/components/chat';

interface ThreadMessage {
  id: string;
  sender: 'user' | 'bot';
  content: string;
}

const ROLE_META: Record<string, { badge: string; name: string; cls: string }> = {
  hr: { badge: 'HR', name: 'HR Assistant', cls: 'role-hr' },
  it: { badge: 'IT', name: 'IT Support', cls: 'role-it' },
  admissions: { badge: 'AD', name: 'Admissions Assistant', cls: 'role-adm' },
};

export default function ChatPage({ params }: { params: { id: string } }) {
  const convId = params.id;
  const [messages, setMessages] = useState<ThreadMessage[]>([]);
  const [meta, setMeta] = useState<{ role_pack: string; title: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [connectionError, setConnectionError] = useState(false);
  const [input, setInput] = useState('');
  const threadRef = useRef<HTMLDivElement>(null);

  const role = meta?.role_pack ?? 'hr';
  const roleMeta = ROLE_META[role] ?? ROLE_META.hr;

  useEffect(() => {
    let active = true;
    setLoading(true);
    setConnectionError(false);

    Promise.all([fetchMessages(convId), fetchConversations()])
      .then(([msgRes, convRes]) => {
        if (!active) return;
        if (msgRes.status === 'success') {
          setMessages(
            msgRes.data.messages.map((m: any) => ({
              id: m.id,
              sender: m.sender,
              content: m.content,
            }))
          );
        }
        if (convRes.status === 'success') {
          const found = convRes.data.conversations.find((c: any) => c.id === convId);
          if (found) setMeta({ role_pack: found.role_pack, title: found.title });
        }
      })
      .catch(() => active && setConnectionError(true))
      .finally(() => active && setLoading(false));

    return () => {
      active = false;
    };
  }, [convId]);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight });
  }, [messages, sending]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setInput('');
    setConnectionError(false);
    setMessages((prev) => [...prev, { id: `local-${Date.now()}`, sender: 'user', content: text }]);
    setSending(true);

    try {
      const res = await sendChatMessage(convId, text, 'chat');
      if (res.status === 'success') {
        setMessages((prev) => [
          ...prev,
          { id: `bot-${Date.now()}`, sender: 'bot', content: res.data.response_text },
        ]);
      }
    } catch (e) {
      setConnectionError(true);
    } finally {
      setSending(false);
    }
  };

  const toThreadRow = (m: ThreadMessage) => {
    if (m.sender === 'user') return <UserMessage key={m.id} text={m.content} />;
    // Live bot responses are plain text; rich card types are composed by role
    // packs in their read-flow slices via the same component library.
    const data: BotMessageData = { type: 'plain_text', text: m.content };
    return <BotMessage key={m.id} message={data} />;
  };

  const isEmpty = !loading && messages.length === 0;

  return (
    <main className={`canvas ${roleMeta.cls}`}>
      <div className="chat-header">
        <button
          className="rail-toggle"
          onClick={() => document.querySelector('.rail')?.classList.toggle('open')}
          aria-label="Toggle sidebar"
        >
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
        <div className="role-icon">{roleMeta.badge}</div>
        <div className="titles">
          <h2>{roleMeta.name}</h2>
          <div className="sub">{meta?.title ?? 'Conversation'}</div>
        </div>
      </div>

      {connectionError && (
        <div className="banner banner-danger" role="alert">
          <svg viewBox="0 0 24 24" fill="none" style={{ width: 15, height: 15 }}>
            <path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
          </svg>
          Connection lost — messages may not send.
        </div>
      )}

      <div className="chat-wrap" style={{ position: 'relative' }}>
        <div
          className="chat-thread"
          id="thread"
          ref={threadRef}
          style={isEmpty ? { display: 'block' } : undefined}
        >
          {loading ? (
            <div className="msg-row bot">
              <div className="avatar-bot" />
              <div className="bubble bot-text" style={{ padding: 0 }}>
                <div className="typing"><span /><span /><span /></div>
              </div>
            </div>
          ) : isEmpty ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div className="empty-state">
                <h3>Ask {roleMeta.name} anything</h3>
                <p>Type a message below to get started.</p>
              </div>
            </div>
          ) : (
            <>
              {messages.map(toThreadRow)}
              {sending && (
                <div className="msg-row bot">
                  <div className="avatar-bot" />
                  <div className="bubble bot-text" style={{ padding: 0 }}>
                    <div className="typing"><span /><span /><span /></div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div className="chat-input">
          <button className="icon-btn mic-idle" type="button" title="Talk mode (coming soon)" disabled>
            <svg viewBox="0 0 24 24" fill="none">
              <rect x="9" y="3" width="6" height="11" rx="3" stroke="currentColor" strokeWidth="1.8" />
              <path d="M5 11a7 7 0 0 0 14 0M12 18v3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
          <input
            type="text"
            placeholder={`Message ${roleMeta.name}…`}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSend();
            }}
            disabled={loading}
          />
          <button className="icon-btn send" type="button" onClick={handleSend} disabled={sending || loading} aria-label="Send">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M4 12l16-7-6 16-2.5-6.5L4 12z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>
    </main>
  );
}
