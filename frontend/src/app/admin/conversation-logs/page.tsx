'use client';

// Conversation Logs page (slice-11): role-pack scoped conversation history
// with filter bar, table of conversations, expandable read-only transcript
// viewer displaying intent + confidence scores per bot message, and pagination.
import { Fragment, useCallback, useEffect, useState } from 'react';
import {
  fetchAdminConversations,
  fetchAdminConversationMessages,
  type ConversationLogFilters,
  type AdminConversationItem,
  type AdminTranscriptData,
} from '@/lib/api';
import { useAdmin } from '@/lib/adminAuth';
import { AdminTopbar } from '@/components/admin/AdminTopbar';

const PAGE_SIZE = 20;

function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  if (isNaN(d.getTime())) return ts;
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function getUserInitials(name: string): string {
  if (!name) return 'U';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function confColor(conf: number | null | undefined): string {
  if (typeof conf !== 'number') return 'var(--text-faint)';
  if (conf >= 0.75) return 'var(--success)';
  if (conf >= 0.5) return 'var(--warn)';
  return 'var(--danger)';
}

type LoadState = 'loading' | 'loaded' | 'empty' | 'error';

interface TranscriptState {
  loading: boolean;
  error?: string | null;
  data?: AdminTranscriptData | null;
}

export default function ConversationLogsPage() {
  const { admin } = useAdmin();
  const [state, setState] = useState<LoadState>('loading');
  const [conversations, setConversations] = useState<AdminConversationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);

  // Expanded row ID for transcript view.
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [transcripts, setTranscripts] = useState<Record<string, TranscriptState>>({});

  // Filter inputs (draft - N15).
  const [actor, setActor] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  // Applied filters (filters only fire on Apply / Clear - N15).
  const [appliedFilters, setAppliedFilters] = useState<ConversationLogFilters>({
    limit: PAGE_SIZE,
    offset: 0,
  });

  const load = useCallback(
    (nextOffset: number, filtersToUse?: ConversationLogFilters) => {
      setState('loading');
      const active = filtersToUse ?? appliedFilters;
      const filters: ConversationLogFilters = {
        ...active,
        limit: PAGE_SIZE,
        offset: nextOffset,
      };

      fetchAdminConversations(filters)
        .then((res) => {
          if (res.status === 'success') {
            const rows: AdminConversationItem[] = res.data.conversations ?? [];
            setConversations(rows);
            setTotal(res.data.total ?? rows.length);
            setState(rows.length === 0 ? 'empty' : 'loaded');
          } else {
            setState('error');
          }
        })
        .catch(() => setState('error'));
    },
    [appliedFilters]
  );

  useEffect(() => {
    load(offset);
  }, [load, offset]);

  const loadTranscript = useCallback((conversationId: string) => {
    setTranscripts((prev) => ({
      ...prev,
      [conversationId]: { loading: true, error: null, data: prev[conversationId]?.data },
    }));

    fetchAdminConversationMessages(conversationId)
      .then((res) => {
        if (res.status === 'success') {
          setTranscripts((prev) => ({
            ...prev,
            [conversationId]: { loading: false, error: null, data: res.data },
          }));
        } else {
          setTranscripts((prev) => ({
            ...prev,
            [conversationId]: { loading: false, error: res.error || 'Failed to load transcript' },
          }));
        }
      })
      .catch((err) => {
        setTranscripts((prev) => ({
          ...prev,
          [conversationId]: { loading: false, error: err.message || 'Failed to load transcript' },
        }));
      });
  }, []);

  const toggleExpand = (conversationId: string) => {
    if (expandedId === conversationId) {
      setExpandedId(null);
    } else {
      setExpandedId(conversationId);
      if (!transcripts[conversationId]?.data) {
        loadTranscript(conversationId);
      }
    }
  };

  const applyFilters = () => {
    setExpandedId(null);
    const newApplied: ConversationLogFilters = {
      actor_id: actor.trim() || undefined,
      from: fromDate || undefined,
      to: toDate || undefined,
      limit: PAGE_SIZE,
      offset: 0,
    };
    setAppliedFilters(newApplied);
    if (offset === 0) load(0, newApplied);
    else setOffset(0);
  };

  const clearFilters = () => {
    setActor('');
    setFromDate('');
    setToDate('');
    setExpandedId(null);
    const cleared: ConversationLogFilters = {
      limit: PAGE_SIZE,
      offset: 0,
    };
    setAppliedFilters(cleared);
    if (offset === 0) load(0, cleared);
    else setOffset(0);
  };

  const rangeStart = total === 0 ? 0 : offset + 1;
  const rangeEnd = Math.min(offset + PAGE_SIZE, total);
  const canPrev = offset > 0;
  const canNext = offset + PAGE_SIZE < total;

  return (
    <main className="canvas">
      <AdminTopbar title="Conversation logs" admin={admin} />

      <div className="filter-bar">
        <input
          aria-label="Search by actor"
          type="text"
          placeholder="Search by user or actor…"
          style={{ minWidth: 200 }}
          value={actor}
          onChange={(e) => setActor(e.target.value)}
        />
        <input
          aria-label="From date"
          type="date"
          value={fromDate}
          onChange={(e) => setFromDate(e.target.value)}
        />
        <span style={{ color: 'var(--text-faint)', fontSize: 13 }}>to</span>
        <input
          aria-label="To date"
          type="date"
          value={toDate}
          onChange={(e) => setToDate(e.target.value)}
        />
        <button className="btn btn-outline btn-sm" type="button" onClick={applyFilters}>
          Apply
        </button>
        <button className="btn btn-ghost btn-sm" type="button" onClick={clearFilters}>
          Clear filters
        </button>
      </div>

      <div className="content-scroll">
        <div className="content-pad">
          <div className="panel" id="conversationPanel">
            {state === 'loading' && (
              <div style={{ padding: 20 }} data-testid="conversations-skeleton">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="skeleton-light skel-line" style={{ width: '100%', margin: '12px 0' }} />
                ))}
              </div>
            )}

            {state === 'error' && (
              <div className="empty-state" style={{ padding: '60px 20px' }}>
                <h3>Couldn&apos;t load conversation logs</h3>
                <p>Something went wrong. Check your connection and try again.</p>
                <button className="btn btn-outline btn-sm" type="button" onClick={() => load(offset)}>
                  Retry
                </button>
              </div>
            )}

            {state === 'empty' && (
              <div className="empty-state" style={{ padding: '60px 20px' }}>
                <h3>No conversations yet</h3>
                <p>Once employees start talking to this role pack&apos;s bot, conversations will show up here.</p>
              </div>
            )}

            {state === 'loaded' && (
              <table>
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Started at</th>
                    <th>Messages</th>
                    <th>Last intent</th>
                    <th style={{ textAlign: 'right' }}>Transcript</th>
                  </tr>
                </thead>
                <tbody>
                  {conversations.map((c) => {
                    const isExpanded = expandedId === c.id;
                    const transcriptState = transcripts[c.id];

                    return (
                      <Fragment key={c.id}>
                        <tr
                          className="row-hover"
                          style={{ cursor: 'pointer' }}
                          onClick={() => toggleExpand(c.id)}
                          data-testid={`conv-row-${c.id}`}
                        >
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                              <div
                                className="avatar-user"
                                style={{
                                  width: 30,
                                  height: 30,
                                  borderRadius: '50%',
                                  background: 'var(--ink-3)',
                                  color: 'var(--text-inv)',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  fontSize: 11,
                                  fontWeight: 700,
                                }}
                              >
                                {getUserInitials(c.user_name || c.user_email || 'User')}
                              </div>
                              <div>
                                <div style={{ fontWeight: 600 }}>{c.user_name || c.user_email || 'User'}</div>
                                {c.user_name && c.user_email && (
                                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{c.user_email}</div>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="mono" style={{ color: 'var(--text-muted)', fontSize: 12.5 }}>
                            {formatTimestamp(c.started_at)}
                          </td>
                          <td>
                            <span className="pill" style={{ fontSize: 12 }}>
                              {c.message_count} {c.message_count === 1 ? 'msg' : 'msgs'}
                            </span>
                          </td>
                          <td>
                            {c.last_intent ? (
                              <span className="var-chip mono" style={{ fontSize: 12 }}>
                                {c.last_intent}
                              </span>
                            ) : (
                              <span style={{ color: 'var(--text-faint)' }}>—</span>
                            )}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <button
                              className="btn btn-ghost btn-sm"
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleExpand(c.id);
                              }}
                            >
                              {isExpanded ? 'Hide transcript ▴' : 'View transcript ▾'}
                            </button>
                          </td>
                        </tr>

                        {isExpanded && (
                          <tr data-testid={`transcript-row-${c.id}`}>
                            <td colSpan={5} style={{ background: 'var(--paper)', padding: 0 }}>
                              {transcriptState?.loading && (
                                <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
                                  <div className="spinner" style={{ margin: '0 auto 8px' }} />
                                  Loading transcript…
                                </div>
                              )}

                              {transcriptState?.error && (
                                <div style={{ padding: 24, textAlign: 'center', color: 'var(--danger)' }}>
                                  <p>{transcriptState.error}</p>
                                  <button
                                    className="btn btn-outline btn-sm"
                                    type="button"
                                    onClick={() => loadTranscript(c.id)}
                                  >
                                    Retry
                                  </button>
                                </div>
                              )}

                              {transcriptState?.data && (
                                <div
                                  style={{
                                    padding: '20px 24px',
                                    borderTop: '1px solid var(--line)',
                                    borderBottom: '1px solid var(--line)',
                                  }}
                                >
                                  <div
                                    style={{
                                      display: 'flex',
                                      alignItems: 'center',
                                      justifyContent: 'space-between',
                                      marginBottom: 16,
                                    }}
                                  >
                                    <div>
                                      <h4 style={{ margin: 0, fontSize: 14, fontWeight: 700 }}>
                                        {c.user_name || c.user_email || 'Transcript'}
                                      </h4>
                                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                        {c.user_email ? `${c.user_email} · ` : ''}started {formatTimestamp(c.started_at)} · read-only transcript
                                      </div>
                                    </div>
                                    <span className="pill" style={{ fontSize: 11 }}>Read-only</span>
                                  </div>

                                  <div
                                    className="chat-thread"
                                    style={{
                                      display: 'flex',
                                      flexDirection: 'column',
                                      gap: 14,
                                      maxHeight: 480,
                                      overflowY: 'auto',
                                      padding: '16px 20px',
                                      background: 'var(--paper-raised)',
                                      borderRadius: 'var(--r-md)',
                                      border: '1px solid var(--line)',
                                    }}
                                  >
                                    {transcriptState.data.messages.length === 0 ? (
                                      <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                                        No messages in this conversation.
                                      </div>
                                    ) : (
                                      transcriptState.data.messages.map((m) => {
                                        if (m.sender === 'user') {
                                          return (
                                            <div
                                              key={m.id}
                                              className="msg-row user"
                                              style={{
                                                alignSelf: 'flex-end',
                                                display: 'flex',
                                                gap: 10,
                                                alignItems: 'flex-end',
                                              }}
                                            >
                                              <div className="bubble user" style={{ maxWidth: 480 }}>
                                                {m.content}
                                              </div>
                                              <div
                                                className="avatar-user"
                                                style={{
                                                  width: 28,
                                                  height: 28,
                                                  borderRadius: '50%',
                                                  background: 'var(--ink-3)',
                                                  color: 'var(--text-inv)',
                                                  display: 'flex',
                                                  alignItems: 'center',
                                                  justifyContent: 'center',
                                                  fontSize: 10,
                                                  fontWeight: 700,
                                                }}
                                              >
                                                {getUserInitials(c.user_name || c.user_email || 'User')}
                                              </div>
                                            </div>
                                          );
                                        }

                                        // Bot message
                                        const rawConf = m.confidence;
                                        const conf =
                                          typeof rawConf === 'number'
                                            ? rawConf > 1
                                              ? rawConf / 100
                                              : rawConf
                                            : null;

                                        return (
                                          <div
                                            key={m.id}
                                            className="msg-row bot"
                                            style={{
                                              alignSelf: 'flex-start',
                                              display: 'flex',
                                              flexDirection: 'column',
                                              alignItems: 'flex-start',
                                              maxWidth: 520,
                                            }}
                                          >
                                            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                                              <div
                                                className="avatar-bot"
                                                style={{
                                                  width: 28,
                                                  height: 28,
                                                  borderRadius: '50%',
                                                  background: 'var(--brand-gradient)',
                                                  display: 'flex',
                                                  alignItems: 'center',
                                                  justifyContent: 'center',
                                                  color: '#fff',
                                                  flexShrink: 0,
                                                }}
                                              >
                                                <svg viewBox="0 0 24 24" fill="none" style={{ width: 14, height: 14 }}>
                                                  <path
                                                    d="M3 12h2.2l1.8-5 3 10 2.6-8 1.6 4.4h2.4l1.8-3.4 1.6 2h2"
                                                    stroke="currentColor"
                                                    strokeWidth="1.8"
                                                    strokeLinecap="round"
                                                    strokeLinejoin="round"
                                                  />
                                                </svg>
                                              </div>
                                              <div className="bubble bot-text" style={{ maxWidth: 480 }}>
                                                {m.content}
                                              </div>
                                            </div>
                                            <div
                                              style={{
                                                marginLeft: 38,
                                                marginTop: 4,
                                                fontSize: 11,
                                                color: 'var(--text-faint)',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: 6,
                                                flexWrap: 'wrap',
                                              }}
                                            >
                                              <span
                                                className="status-dot"
                                                style={{
                                                  width: 8,
                                                  height: 8,
                                                  borderRadius: '50%',
                                                  display: 'inline-block',
                                                  background: confColor(conf),
                                                }}
                                              />
                                              <span className="mono" style={{ fontWeight: 600, color: 'var(--text)' }}>
                                                {m.intent_name || 'unknown_intent'}
                                              </span>
                                              <span>·</span>
                                              <span>
                                                confidence {conf !== null ? `${conf.toFixed(2)} (${Math.round(conf * 100)}%)` : '—'}
                                              </span>
                                            </div>
                                          </div>
                                        );
                                      })
                                    )}
                                  </div>
                                </div>
                              )}
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {(state === 'loaded' || state === 'empty') && (
        <div className="pagination">
          <span>
            {rangeStart}–{rangeEnd} of {total}
          </span>
          <div className="spacer" style={{ flex: 1 }} />
          <button
            className="btn btn-outline btn-sm"
            type="button"
            disabled={!canPrev}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          >
            Previous
          </button>
          <button
            className="btn btn-outline btn-sm"
            type="button"
            disabled={!canNext}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Next
          </button>
        </div>
      )}
    </main>
  );
}
