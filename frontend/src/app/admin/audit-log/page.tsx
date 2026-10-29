'use client';

// Audit Log page (slice-07): filter bar + results table with expandable JSONB
// details + pagination. Scoped to the admin's role pack by the backend.
import { Fragment, useCallback, useEffect, useState } from 'react';
import { fetchAuditLog, type AuditLogFilters } from '@/lib/api';
import { useAdmin } from '@/lib/adminAuth';
import { AdminTopbar } from '@/components/admin/AdminTopbar';

interface AuditEntry {
  id: string;
  actor_id: string | null;
  actor_name: string | null;
  action_type: string;
  reference_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

const PAGE_SIZE = 20;

// Recorded action types for the filter dropdown (M9c).
const ACTION_OPTIONS = [
  { value: '', label: 'All actions' },
  { value: 'leave_submitted', label: 'Leave submitted' },
  { value: 'ticket_created', label: 'Ticket created' },
  { value: 'password_reset_initiated', label: 'Password reset initiated' },
  { value: 'intent_created', label: 'Intent created' },
  { value: 'intent_updated', label: 'Intent updated' },
  { value: 'intent_deleted', label: 'Intent deleted' },
  { value: 'template_edited', label: 'Template edited' },
  { value: 'variant_edited', label: 'Variant edited' },
  { value: 'variant_deleted', label: 'Variant deleted' },
];

function humanizeAction(action: string): string {
  const s = action.replace(/_/g, ' ').trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

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

type LoadState = 'loading' | 'loaded' | 'empty' | 'error';

export default function AuditLogPage() {
  const { admin } = useAdmin();
  const [state, setState] = useState<LoadState>('loading');
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null);

  // Draft filter inputs; applied to the query on submit / clear.
  const [actionType, setActionType] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [actor, setActor] = useState('');

  const load = useCallback(
    (nextOffset: number) => {
      setState('loading');
      const filters: AuditLogFilters = {
        action_type: actionType || undefined,
        actor_id: actor || undefined,
        from: fromDate || undefined,
        to: toDate || undefined,
        limit: PAGE_SIZE,
        offset: nextOffset,
      };
      fetchAuditLog(filters)
        .then((res) => {
          if (res.status === 'success') {
            const rows: AuditEntry[] = res.data.entries ?? [];
            setEntries(rows);
            setTotal(res.data.total ?? rows.length);
            setState(rows.length === 0 ? 'empty' : 'loaded');
          } else {
            setState('error');
          }
        })
        .catch(() => setState('error'));
    },
    [actionType, actor, fromDate, toDate]
  );

  // Reload whenever the page offset changes (and on first mount).
  useEffect(() => {
    load(offset);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset]);

  const applyFilters = () => {
    setExpanded(null);
    if (offset === 0) load(0);
    else setOffset(0); // triggers reload via effect
  };

  const clearFilters = () => {
    setActionType('');
    setFromDate('');
    setToDate('');
    setActor('');
    setExpanded(null);
    // Reload cleared query.
    setState('loading');
    fetchAuditLog({ limit: PAGE_SIZE, offset: 0 })
      .then((res) => {
        if (res.status === 'success') {
          const rows: AuditEntry[] = res.data.entries ?? [];
          setEntries(rows);
          setTotal(res.data.total ?? rows.length);
          setOffset(0);
          setState(rows.length === 0 ? 'empty' : 'loaded');
        } else {
          setState('error');
        }
      })
      .catch(() => setState('error'));
  };

  const rangeStart = total === 0 ? 0 : offset + 1;
  const rangeEnd = Math.min(offset + PAGE_SIZE, total);
  const canPrev = offset > 0;
  const canNext = offset + PAGE_SIZE < total;

  return (
    <main className="canvas">
      <AdminTopbar title="Audit log" admin={admin} />

      <div className="filter-bar">
        <select
          aria-label="Filter by action"
          value={actionType}
          onChange={(e) => setActionType(e.target.value)}
        >
          {ACTION_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <input aria-label="From date" type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
        <span style={{ color: 'var(--text-faint)', fontSize: 13 }}>to</span>
        <input aria-label="To date" type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} />
        <input
          aria-label="Search by actor"
          type="text"
          placeholder="Search by actor…"
          style={{ minWidth: 180 }}
          value={actor}
          onChange={(e) => setActor(e.target.value)}
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
          <div className="panel" id="logPanel">
            {state === 'loading' && (
              <div style={{ padding: 20 }} data-testid="audit-skeleton">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="skeleton-light skel-line" style={{ width: '100%', margin: '12px 0' }} />
                ))}
              </div>
            )}

            {state === 'error' && (
              <div className="empty-state" style={{ padding: '60px 20px' }}>
                <h3>Couldn&apos;t load the audit log</h3>
                <p>Something went wrong. Check your connection and try again.</p>
                <button className="btn btn-outline btn-sm" type="button" onClick={() => load(offset)}>
                  Retry
                </button>
              </div>
            )}

            {state === 'empty' && (
              <div className="empty-state" style={{ padding: '60px 20px' }}>
                <h3>No audit entries</h3>
                <p>No events match the current filters for your role pack.</p>
              </div>
            )}

            {state === 'loaded' && (
              <table>
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Actor</th>
                    <th>Action</th>
                    <th>Reference</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {entries.map((e) => {
                    const isOpen = expanded === e.id;
                    return (
                      <Fragment key={e.id}>
                        <tr
                          className="row-hover"
                          style={{ cursor: 'pointer' }}
                          onClick={() => setExpanded(isOpen ? null : e.id)}
                        >
                          <td className="mono" style={{ color: 'var(--text-muted)', fontSize: 12.5 }}>
                            {formatTimestamp(e.created_at)}
                          </td>
                          <td style={{ fontWeight: 600 }}>{e.actor_name || e.actor_id || '—'}</td>
                          <td>{humanizeAction(e.action_type)}</td>
                          <td className="mono" style={{ fontSize: 12.5 }}>{e.reference_id || '—'}</td>
                          <td style={{ textAlign: 'right', color: 'var(--text-faint)' }}>{isOpen ? '▾' : '▸'}</td>
                        </tr>
                        {isOpen && (
                          <tr data-testid={`detail-${e.id}`}>
                            <td colSpan={5} style={{ background: 'var(--paper)' }}>
                              <pre
                                className="mono"
                                style={{ margin: 0, fontSize: 12, whiteSpace: 'pre-wrap', color: 'var(--text-muted)' }}
                              >
                                {JSON.stringify(e.details ?? {}, null, 2)}
                              </pre>
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
          <button className="btn btn-outline btn-sm" type="button" disabled={!canPrev} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
            Previous
          </button>
          <button className="btn btn-outline btn-sm" type="button" disabled={!canNext} onClick={() => setOffset(offset + PAGE_SIZE)}>
            Next
          </button>
        </div>
      )}
    </main>
  );
}
