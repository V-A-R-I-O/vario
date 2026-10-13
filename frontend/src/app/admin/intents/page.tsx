'use client';

// Intent List page framework (slice-07): the table shell for the admin's role
// pack with type badges, needs-retrain badge, a retrain-status banner, and
// loading / empty / error states. Row data comes from GET /api/admin/intents
// (built in slice-08); intent CRUD / Create-Edit live in slice-08 too.
import { useEffect, useState } from 'react';
import { fetchIntents } from '@/lib/api';
import { useAdmin } from '@/lib/adminAuth';
import { AdminTopbar } from '@/components/admin/AdminTopbar';

interface Intent {
  id: string;
  name: string;
  intent_type: 'dynamic_workflow' | 'static_faq';
  needs_retrain: boolean;
  updated_at: string;
  training_phrases?: unknown[];
  phrase_count?: number;
}

type LoadState = 'loading' | 'loaded' | 'empty' | 'error';

function formatDate(ts: string): string {
  const d = new Date(ts);
  if (isNaN(d.getTime())) return ts;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function phraseCount(i: Intent): number {
  if (typeof i.phrase_count === 'number') return i.phrase_count;
  return Array.isArray(i.training_phrases) ? i.training_phrases.length : 0;
}

export default function IntentListPage() {
  const { admin } = useAdmin();
  const [state, setState] = useState<LoadState>('loading');
  const [intents, setIntents] = useState<Intent[]>([]);

  const load = () => {
    setState('loading');
    fetchIntents()
      .then((res) => {
        if (res.status === 'success') {
          const rows: Intent[] = res.data.intents ?? [];
          setIntents(rows);
          setState(rows.length === 0 ? 'empty' : 'loaded');
        } else {
          setState('error');
        }
      })
      .catch(() => setState('error'));
  };

  useEffect(load, []);

  const retrainCount = intents.filter((i) => i.needs_retrain).length;

  return (
    <main className="canvas">
      <AdminTopbar title={admin ? `${admin.badge} intents` : 'Intents'} admin={admin} />

      <div className="content-scroll">
        {state === 'loading' && <IntentTableSkeleton />}

        {state === 'error' && (
          <div className="empty-state" style={{ paddingTop: 100 }}>
            <div className="icon" style={{ borderColor: 'var(--danger)', background: 'var(--danger-tint)' }}>
              <svg viewBox="0 0 24 24" fill="none" style={{ width: 20, height: 20, color: 'var(--danger)' }}>
                <path d="M12 8v5M12 16h.01M12 3 2 21h20L12 3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
              </svg>
            </div>
            <h3>Couldn&apos;t load intents</h3>
            <p>Something went wrong fetching intents for your role pack. Check your connection and try again.</p>
            <button className="btn btn-outline btn-sm" type="button" onClick={load}>
              Retry
            </button>
          </div>
        )}

        {state === 'empty' && (
          <div className="empty-state" style={{ paddingTop: 100 }}>
            <div className="icon">
              <svg viewBox="0 0 24 24" fill="none" style={{ width: 22, height: 22, color: 'var(--text-faint)' }}>
                <path d="M4 6h16M4 12h16M4 18h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
            </div>
            <h3>No intents configured</h3>
            <p>Static FAQs you create will show up here. Pre-seeded workflows should already be listed — check with the platform team if you expect to see some.</p>
          </div>
        )}

        {state === 'loaded' && (
          <>
            <div className="content-pad" style={{ paddingBottom: 0 }}>
              {retrainCount > 0 && (
                <div
                  className="panel"
                  role="status"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: '12px 16px',
                    marginBottom: 18,
                    borderColor: 'var(--warn)',
                    background: 'var(--warn-tint)',
                  }}
                >
                  <svg viewBox="0 0 24 24" fill="none" style={{ width: 16, height: 16, color: 'var(--warn)' }}>
                    <path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
                  </svg>
                  <span style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--warn)' }}>
                    {retrainCount} intent{retrainCount > 1 ? 's' : ''} have changes since the last training run.
                  </span>
                </div>
              )}
            </div>
            <div className="panel" style={{ margin: '0 28px 28px' }}>
              <table>
                <thead>
                  <tr>
                    <th>Intent</th>
                    <th>Type</th>
                    <th>Training phrases</th>
                    <th>Status</th>
                    <th>Last updated</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {intents.map((i) => {
                    const isWorkflow = i.intent_type === 'dynamic_workflow';
                    return (
                      <tr className="row-hover" key={i.id}>
                        <td className="mono" style={{ fontWeight: 600 }}>{i.name}</td>
                        <td>
                          {isWorkflow ? (
                            <span className="badge badge-workflow">Dynamic workflow</span>
                          ) : (
                            <span className="badge badge-faq">Static FAQ</span>
                          )}
                        </td>
                        <td>{phraseCount(i)} phrases</td>
                        <td>
                          {i.needs_retrain ? (
                            <span className="badge badge-warn">Needs retrain</span>
                          ) : (
                            <span style={{ color: 'var(--text-faint)', fontSize: 12.5 }}>Up to date</span>
                          )}
                        </td>
                        <td style={{ color: 'var(--text-muted)' }}>{formatDate(i.updated_at)}</td>
                        <td style={{ textAlign: 'right' }}>
                          <button className="btn btn-outline btn-sm" type="button">
                            Edit
                          </button>
                          <button
                            className="btn btn-ghost btn-sm"
                            type="button"
                            style={{ color: 'var(--danger-dark)' }}
                            disabled={isWorkflow}
                            title={isWorkflow ? 'Dynamic workflows cannot be deleted' : undefined}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </main>
  );
}

function IntentTableSkeleton() {
  const cells = ['64%', '46%', '38%', '52%', '34%'];
  return (
    <div className="panel" style={{ margin: '24px 28px' }} data-testid="intent-skeleton">
      <table>
        <thead>
          <tr>
            <th>Intent</th>
            <th>Type</th>
            <th>Training phrases</th>
            <th>Status</th>
            <th>Last updated</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: 5 }).map((_, r) => (
            <tr className="skel-row" key={r}>
              {cells.map((w, c) => (
                <td key={c}>
                  <div className="skeleton-light skel-line" style={{ width: w }} />
                </td>
              ))}
              <td />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
