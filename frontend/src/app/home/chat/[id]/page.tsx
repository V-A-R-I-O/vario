'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchMessages, sendChatMessage, fetchConversations } from '@/lib/api';
import { useSpeechRecognition } from '@/lib/useSpeechRecognition';
import { BotMessage, UserMessage, type BotMessageData } from '@/components/chat';

interface ThreadMessage {
  id: string;
  sender: 'user' | 'bot';
  content: string;
  // Talk mode (slice-06): audio attached to a bot reply, replayable via speaker.
  audioBase64?: string | null;
  audioContentType?: string | null;
}

type TalkState = 'idle' | 'listening' | 'processing';

const ROLE_META: Record<string, { badge: string; name: string; cls: string }> = {
  hr: { badge: 'HR', name: 'HR Assistant', cls: 'role-hr' },
  it: { badge: 'IT', name: 'IT Support', cls: 'role-it' },
  admissions: { badge: 'AD', name: 'Admissions Assistant', cls: 'role-adm' },
};

function audioSrc(base64: string, contentType?: string | null): string {
  return `data:${contentType || 'audio/mp3'};base64,${base64}`;
}

export default function ChatPage({ params }: { params: { id: string } }) {
  const convId = params.id;
  const [messages, setMessages] = useState<ThreadMessage[]>([]);
  const [meta, setMeta] = useState<{ role_pack: string; title: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [connectionError, setConnectionError] = useState(false);
  const [input, setInput] = useState('');
  const threadRef = useRef<HTMLDivElement>(null);

  // Talk mode (slice-06) state.
  const [talkActive, setTalkActive] = useState(false);
  const [talkState, setTalkState] = useState<TalkState>('idle');
  const [ttsUnavailable, setTtsUnavailable] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const talkActiveRef = useRef(false);
  useEffect(() => {
    talkActiveRef.current = talkActive;
  }, [talkActive]);

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

  // --- Core send; `mode` decides whether the reply is spoken --------------
  const sendMessage = useCallback(
    async (text: string, mode: 'chat' | 'talk'): Promise<ThreadMessage | null> => {
      setConnectionError(false);
      setMessages((prev) => [...prev, { id: `local-${Date.now()}`, sender: 'user', content: text }]);
      setSending(true);
      try {
        const res = await sendChatMessage(convId, text, mode);
        if (res.status === 'success') {
          const botMsg: ThreadMessage = {
            id: `bot-${Date.now()}`,
            sender: 'bot',
            content: res.data.response_text,
            // Only keep audio when TTS actually succeeded.
            audioBase64: res.data.tts_available ? res.data.audio_base64 ?? null : null,
            audioContentType: res.data.audio_content_type ?? null,
          };
          setMessages((prev) => [...prev, botMsg]);
          return botMsg;
        }
        return null;
      } catch {
        setConnectionError(true);
        return null;
      } finally {
        setSending(false);
      }
    },
    [convId]
  );

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput('');
    await sendMessage(text, 'chat');
  };

  // --- Audio playback + hands-free loop -----------------------------------
  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
  }, []);

  const playAudio = useCallback(
    (base64: string, contentType: string | null | undefined, onDone?: () => void) => {
      stopAudio();
      const audio = new Audio(audioSrc(base64, contentType));
      audioRef.current = audio;
      audio.onended = () => {
        audioRef.current = null;
        onDone?.();
      };
      audio.play().catch(() => onDone?.());
    },
    [stopAudio]
  );

  // Declared before the STT hook so the transcript handler can call it.
  const startListeningRef = useRef<() => void>(() => {});

  const handleTranscript = useCallback(
    async (transcript: string) => {
      setTalkState('processing');
      const reply = await sendMessage(transcript, 'talk');
      setInput('');
      if (!reply) {
        // Network/connection error — drop out of the hands-free loop.
        setTalkState('idle');
        return;
      }
      if (reply.audioBase64) {
        // Auto-play the spoken reply, then resume listening (hands-free loop).
        playAudio(reply.audioBase64, reply.audioContentType, () => {
          if (talkActiveRef.current) startListeningRef.current();
        });
      } else {
        // TTS unavailable — show the banner and leave talk mode.
        setTtsUnavailable(true);
        setTalkActive(false);
        setTalkState('idle');
      }
    },
    [sendMessage, playAudio]
  );

  const stt = useSpeechRecognition({ onResult: handleTranscript });

  // Reflect the live transcript into the input bar while listening.
  useEffect(() => {
    if (stt.listening) setInput(stt.transcript);
  }, [stt.listening, stt.transcript]);

  const startListening = useCallback(() => {
    setTtsUnavailable(false);
    setTalkState('listening');
    stt.start();
  }, [stt]);
  useEffect(() => {
    startListeningRef.current = startListening;
  }, [startListening]);

  const startTalk = useCallback(() => {
    if (!stt.supported) return;
    setTalkActive(true);
    startListening();
  }, [stt.supported, startListening]);

  const exitTalk = useCallback(() => {
    setTalkActive(false);
    setTalkState('idle');
    stt.stop();
    stopAudio();
    setInput('');
  }, [stt, stopAudio]);

  const toThreadRow = (m: ThreadMessage) => {
    if (m.sender === 'user') return <UserMessage key={m.id} text={m.content} />;
    const data: BotMessageData = { type: 'plain_text', text: m.content };
    const onReplay = m.audioBase64
      ? () => playAudio(m.audioBase64 as string, m.audioContentType)
      : undefined;
    return <BotMessage key={m.id} message={data} onReplay={onReplay} />;
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
          <div className="sub">{talkActive ? 'Talk mode · hands-free' : meta?.title ?? 'Conversation'}</div>
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

      {ttsUnavailable && (
        <div className="banner banner-warn" role="alert">
          <svg viewBox="0 0 24 24" fill="none" style={{ width: 15, height: 15 }}>
            <path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
          </svg>
          Talk mode is temporarily unavailable.
          <button className="btn btn-outline btn-sm" type="button" onClick={() => setTtsUnavailable(false)}>
            Switch to text
          </button>
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

        <div className="chat-input" id="idleInput">
          <button
            className={`icon-btn ${talkActive ? 'mic-on' : 'mic-idle'}`}
            type="button"
            title={stt.supported ? 'Talk mode' : 'Voice input not supported in this browser'}
            aria-label="Talk mode"
            onClick={startTalk}
            disabled={!stt.supported || loading}
          >
            <svg viewBox="0 0 24 24" fill="none">
              <rect x="9" y="3" width="6" height="11" rx="3" stroke="currentColor" strokeWidth="1.8" />
              <path d="M5 11a7 7 0 0 0 14 0M12 18v3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
          <input
            type="text"
            placeholder={
              stt.supported
                ? `Message ${roleMeta.name}, or tap the mic to talk…`
                : `Message ${roleMeta.name}…`
            }
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

        {talkActive && (
          <div id="overlay" className="talk-overlay" role="dialog" aria-label="Talk mode">
            <button
              className="btn btn-outline"
              type="button"
              style={{ position: 'absolute', top: 16, right: 16, borderColor: 'var(--ink-line)', color: 'var(--text-inv)' }}
              onClick={exitTalk}
            >
              Switch to text
            </button>
            <div className={`talk-ring ${talkState === 'listening' ? 'listening' : ''}`} id="ring">
              <div className="core">
                <svg viewBox="0 0 24 24" fill="none">
                  <rect x="9" y="3" width="6" height="11" rx="3" stroke="#0D2622" strokeWidth="1.8" />
                  <path d="M5 11a7 7 0 0 0 14 0M12 18v3" stroke="#0D2622" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
              </div>
            </div>
            <div className="talk-status" id="status">
              {talkState === 'processing' ? 'Processing…' : 'Listening…'}
            </div>
            <div className="talk-transcript" id="transcript">
              {stt.transcript ? `“${stt.transcript}”` : ''}
            </div>
            <div className="talk-sub">Speak naturally — I&apos;ll respond out loud and keep listening.</div>
          </div>
        )}
      </div>
    </main>
  );
}
