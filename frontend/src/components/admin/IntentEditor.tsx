'use client';

// Create/Edit Intent (slice-08). Two modes:
//  - Mode A (dynamic_workflow): read-only System Key + available-variable chips,
//    response textarea with an "unknown variable" warning. Name + variables fixed.
//  - Mode B (static_faq): validated intent name + variable-free response textarea.
// Shared: training-phrases add/delete + Generate Similar (stub until slice-09),
// Allow-rephrasing toggle + editable/deletable variant list, Save/Cancel.
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAdmin } from '@/lib/adminAuth';
import { AdminTopbar } from '@/components/admin/AdminTopbar';
import {
  createIntent,
  deleteVariant as apiDeleteVariant,
  fetchIntents,
  generatePhrases,
  updateIntent,
  updateTemplate,
  updateVariant,
} from '@/lib/api';

interface Phrase {
  id?: string; // present if persisted
  phrase_text: string;
}
interface Variant {
  id: string;
  variant_text: string;
  position?: number;
}
interface LoadedIntent {
  id: string;
  name: string;
  intent_type: 'dynamic_workflow' | 'static_faq';
  training_phrases: Phrase[];
  response_template?: {
    id: string;
    template_key: string;
    base_text: string;
    allow_rephrasing: boolean;
    available_variables: string[];
    variants: Variant[];
  } | null;
}

function placeholdersIn(text: string): string[] {
  const re = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g;
  const out: string[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) out.push(m[1]);
  return out;
}

export function IntentEditor({ intentId }: { intentId?: string }) {
  const router = useRouter();
  const { admin } = useAdmin();
  const isCreate = !intentId;

  const [loadState, setLoadState] = useState<'loading' | 'ready' | 'notfound'>(
    isCreate ? 'ready' : 'loading'
  );
  const [loaded, setLoaded] = useState<LoadedIntent | null>(null);

  // Editable state.
  const [name, setName] = useState('');
  const [baseText, setBaseText] = useState('');
  const [allowRephrasing, setAllowRephrasing] = useState(true);
  const [phrases, setPhrases] = useState<Phrase[]>([]);
  const [removedPhraseIds, setRemovedPhraseIds] = useState<string[]>([]);
  const [variants, setVariants] = useState<Variant[]>([]);
  const [newPhrase, setNewPhrase] = useState('');
  const [suggestions, setSuggestions] = useState<string[] | null>(null);
  const [editingSuggestionIndex, setEditingSuggestionIndex] = useState<number | null>(null);
  const [editingSuggestionText, setEditingSuggestionText] = useState('');
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mode: 'workflow' | 'faq' = loaded?.intent_type === 'dynamic_workflow' ? 'workflow' : 'faq';
  const availableVariables = loaded?.response_template?.available_variables ?? [];

  useEffect(() => {
    if (isCreate) return;
    fetchIntents()
      .then((res) => {
        if (res.status !== 'success') return setLoadState('notfound');
        const found: LoadedIntent | undefined = res.data.intents.find((i: any) => i.id === intentId);
        if (!found) return setLoadState('notfound');
        setLoaded(found);
        setName(found.name);
        setBaseText(found.response_template?.base_text ?? '');
        setAllowRephrasing(found.response_template?.allow_rephrasing ?? true);
        setPhrases(found.training_phrases ?? []);
        setVariants(found.response_template?.variants ?? []);
        setLoadState('ready');
      })
      .catch(() => setLoadState('notfound'));
  }, [intentId, isCreate]);

  // Mode A: warn on any placeholder not in the allowed variable list.
  const unknownVar = useMemo(() => {
    if (mode !== 'workflow') return null;
    const bad = placeholdersIn(baseText).find((v) => !availableVariables.includes(v));
    return bad ?? null;
  }, [mode, baseText, availableVariables]);

  const addPhrase = () => {
    const t = newPhrase.trim();
    if (!t) return;
    setPhrases((p) => [...p, { phrase_text: t }]);
    setNewPhrase('');
  };

  const removePhrase = (idx: number) => {
    setPhrases((prev) => {
      const target = prev[idx];
      if (target.id) setRemovedPhraseIds((r) => [...r, target.id as string]);
      return prev.filter((_, i) => i !== idx);
    });
  };

  const handleGenerate = async () => {
    if (!intentId) return;
    setGenerating(true);
    try {
      const res = await generatePhrases(intentId);
      if (res.status === 'success') setSuggestions(res.data.generated_phrases ?? []);
    } catch {
      setSuggestions([]);
    } finally {
      setGenerating(false);
    }
  };

  const acceptSuggestion = (text: string) => {
    setPhrases((p) => [...p, { phrase_text: text }]);
    setSuggestions((s) => (s ? s.filter((x) => x !== text) : s));
    if (editingSuggestionIndex !== null) cancelEditSuggestion();
  };
  const rejectSuggestion = (text: string) => {
    setSuggestions((s) => (s ? s.filter((x) => x !== text) : s));
    if (editingSuggestionIndex !== null) cancelEditSuggestion();
  };
  const startEditSuggestion = (idx: number, text: string) => {
    setEditingSuggestionIndex(idx);
    setEditingSuggestionText(text);
  };
  const cancelEditSuggestion = () => {
    setEditingSuggestionIndex(null);
    setEditingSuggestionText('');
  };
  const saveEditedSuggestion = (idx: number) => {
    const text = editingSuggestionText.trim();
    if (!text) return;
    setPhrases((p) => [...p, { phrase_text: text }]);
    setSuggestions((s) => (s ? s.filter((_, i) => i !== idx) : s));
    cancelEditSuggestion();
  };
  const acceptAll = () => {
    if (!suggestions) return;
    setPhrases((p) => [...p, ...suggestions.map((phrase_text) => ({ phrase_text }))]);
    setSuggestions([]);
    cancelEditSuggestion();
  };

  const editVariantText = (id: string, text: string) => {
    setVariants((vs) => vs.map((v) => (v.id === id ? { ...v, variant_text: text } : v)));
  };

  const handleDeleteVariant = async (id: string) => {
    try {
      const res = await apiDeleteVariant(id);
      if (res.status === 'success') setVariants((vs) => vs.filter((v) => v.id !== id));
    } catch (e: any) {
      setError(e?.message || 'Could not delete variant');
    }
  };

  const handleSave = async () => {
    setError(null);
    if (mode === 'faq' && !name.trim()) {
      setError('Intent name is required.');
      return;
    }
    if (isCreate && phrases.length === 0) {
      setError('Add at least one training phrase.');
      return;
    }
    setSaving(true);
    try {
      if (isCreate) {
        const res = await createIntent({
          name: name.trim(),
          training_phrases: phrases.map((p) => p.phrase_text),
          response_template: { base_text: baseText, allow_rephrasing: allowRephrasing },
        });
        if (res.status !== 'success') throw new Error(res.error || 'Create failed');
      } else if (loaded) {
        // Intent: rename (FAQ only) + phrase add/remove.
        const update: { name?: string; training_phrases?: { add?: string[]; remove?: string[] } } = {};
        if (mode === 'faq' && name.trim() !== loaded.name) update.name = name.trim();
        const added = phrases.filter((p) => !p.id).map((p) => p.phrase_text);
        if (added.length || removedPhraseIds.length) {
          update.training_phrases = { add: added, remove: removedPhraseIds };
        }
        if (update.name !== undefined || update.training_phrases) {
          await updateIntent(loaded.id, update);
        }
        // Template base text + rephrasing toggle (update only if changed - M9a).
        if (loaded.response_template) {
          const templateChanged =
            loaded.response_template.base_text !== baseText ||
            loaded.response_template.allow_rephrasing !== allowRephrasing;
          if (templateChanged) {
            await updateTemplate(loaded.response_template.id, {
              base_text: baseText,
              allow_rephrasing: allowRephrasing,
            });
          }
          // Persist any inline variant text edits.
          const original = loaded.response_template.variants;
          await Promise.all(
            variants
              .filter((v) => {
                const o = original.find((ov) => ov.id === v.id);
                return o && o.variant_text !== v.variant_text;
              })
              .map((v) => updateVariant(v.id, v.variant_text))
          );
        }
      }
      router.push('/admin/intents');
    } catch (e: any) {
      setError(e?.message || 'Save failed');
      setSaving(false);
    }
  };

  if (loadState === 'loading') {
    return (
      <main className="canvas">
        <AdminTopbar title="Edit intent" admin={admin} />
        <div className="content-scroll">
          <div className="content-pad" data-testid="editor-skeleton">
            <div className="skeleton-light skel-line" style={{ width: '40%', margin: '16px 0' }} />
            <div className="skeleton-light skel-line" style={{ width: '80%', margin: '16px 0' }} />
          </div>
        </div>
      </main>
    );
  }

  if (loadState === 'notfound') {
    return (
      <main className="canvas">
        <AdminTopbar title="Edit intent" admin={admin} />
        <div className="content-scroll">
          <div className="empty-state" style={{ paddingTop: 100 }}>
            <h3>Intent not found</h3>
            <p>It may have been deleted, or belongs to another role pack.</p>
            <button className="btn btn-outline btn-sm" type="button" onClick={() => router.push('/admin/intents')}>
              Back to intents
            </button>
          </div>
        </div>
      </main>
    );
  }

  const title = isCreate
    ? 'New FAQ'
    : `Edit intent · ${loaded?.name ?? ''}`;

  return (
    <main className="canvas">
      <AdminTopbar title={title} admin={admin} />

      <div className="content-scroll">
        <div className="content-pad" style={{ maxWidth: 640 }}>
          {error && (
            <div className="banner banner-danger" role="alert" style={{ marginBottom: 16, borderRadius: 8 }}>
              {error}
            </div>
          )}

          {/* Mode-specific identity + response block */}
          <div className="panel panel-pad" style={{ marginBottom: 16 }}>
            {mode === 'workflow' ? (
              <>
                <div className="field">
                  <label>System key</label>
                  <input
                    aria-label="System key"
                    value={loaded?.response_template?.template_key ?? ''}
                    disabled
                    style={{ background: 'var(--paper)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 13 }}
                  />
                  <div className="hint">
                    Pre-seeded by the development team — the key and available variables can&apos;t be changed here.
                  </div>
                </div>
                <div className="field">
                  <label>Available variables</label>
                  <div>
                    {availableVariables.length === 0 && (
                      <span style={{ color: 'var(--text-faint)', fontSize: 12.5 }}>None</span>
                    )}
                    {availableVariables.map((v) => (
                      <span className="var-chip" key={v}>{`{${v}}`}</span>
                    ))}
                  </div>
                </div>
                <div className="field" style={{ marginBottom: 6 }}>
                  <label>Response template</label>
                  <textarea aria-label="Response template" value={baseText} onChange={(e) => setBaseText(e.target.value)} />
                </div>
                {unknownVar && (
                  <div
                    role="alert"
                    style={{ background: 'var(--warn-tint)', color: 'var(--warn)', borderRadius: 6, padding: '9px 12px', fontSize: 12.5, fontWeight: 600, marginBottom: 8 }}
                  >
                    Unknown variable {`{${unknownVar}}`}. Only the listed variables are available.
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="field">
                  <label>Intent name</label>
                  <input
                    aria-label="Intent name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="ask_wfh_policy"
                  />
                  <div className="hint">Lowercase, no spaces — used internally to identify this FAQ.</div>
                </div>
                <div className="field" style={{ marginBottom: 0 }}>
                  <label>Response template</label>
                  <textarea
                    aria-label="Response template"
                    style={{ fontFamily: 'var(--font-ui)' }}
                    value={baseText}
                    onChange={(e) => setBaseText(e.target.value)}
                  />
                </div>
              </>
            )}
          </div>

          {/* Training phrases */}
          <div className="panel panel-pad" style={{ marginBottom: 16 }}>
            <div className="section-title">Training phrases</div>
            <div id="phraseList">
              {phrases.map((p, idx) => (
                <div className="phrase-row" key={p.id ?? `new-${idx}`}>
                  <span>{p.phrase_text}</span>
                  <button className="x" type="button" aria-label="Remove phrase" onClick={() => removePhrase(idx)}>
                    ×
                  </button>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <input
                aria-label="Add a training phrase"
                placeholder="Add a training phrase…"
                style={{ flex: 1, padding: '9px 12px', border: '1px solid var(--line-strong)', borderRadius: 'var(--r-sm)', fontSize: 13.5, fontFamily: 'inherit' }}
                value={newPhrase}
                onChange={(e) => setNewPhrase(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addPhrase()}
              />
              <button className="btn btn-outline btn-sm" type="button" onClick={addPhrase}>
                Add
              </button>
            </div>

            <div className="divider" />

            <button className="btn btn-outline" type="button" onClick={handleGenerate} disabled={generating || isCreate}>
              {generating && <span className="spinner" />}
              {generating ? 'Generating…' : 'Generate similar'}
            </button>
            {isCreate && (
              <div className="hint" style={{ marginTop: 6 }}>
                Save the FAQ first to generate similar phrases.
              </div>
            )}

            {suggestions && (
              <div style={{ marginTop: 14 }}>
                <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginBottom: 8 }}>
                  {suggestions.length === 0
                    ? 'No suggestions available.'
                    : `${suggestions.length} suggestion${suggestions.length > 1 ? 's' : ''} — review before adding to training data.`}
                </div>
                <div>
                  {suggestions.map((s, idx) => {
                    const isEditing = editingSuggestionIndex === idx;
                    return (
                      <div className="gen-phrase-row" key={`${s}-${idx}`}>
                        {isEditing ? (
                          <>
                            <input
                              aria-label={`Edit phrase ${s}`}
                              value={editingSuggestionText}
                              onChange={(e) => setEditingSuggestionText(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') saveEditedSuggestion(idx);
                                if (e.key === 'Escape') cancelEditSuggestion();
                              }}
                              style={{
                                flex: 1,
                                padding: '4px 8px',
                                border: '1px solid var(--brand-b)',
                                borderRadius: 'var(--r-sm)',
                                fontSize: 13.5,
                                fontFamily: 'inherit',
                              }}
                              autoFocus
                            />
                            <div className="actions">
                              <button
                                type="button"
                                title="Accept edited"
                                aria-label={`Accept ${s}`}
                                onClick={() => saveEditedSuggestion(idx)}
                              >
                                ✅
                              </button>
                              <button
                                type="button"
                                title="Cancel edit"
                                aria-label={`Cancel edit ${s}`}
                                onClick={cancelEditSuggestion}
                              >
                                ✕
                              </button>
                            </div>
                          </>
                        ) : (
                          <>
                            <span>{s}</span>
                            <div className="actions">
                              <button
                                type="button"
                                title="Accept"
                                aria-label={`Accept ${s}`}
                                onClick={() => acceptSuggestion(s)}
                              >
                                ✅
                              </button>
                              <button
                                type="button"
                                title="Edit"
                                aria-label={`Edit ${s}`}
                                onClick={() => startEditSuggestion(idx, s)}
                              >
                                ✏️
                              </button>
                              <button
                                type="button"
                                title="Reject"
                                aria-label={`Reject ${s}`}
                                onClick={() => rejectSuggestion(s)}
                              >
                                🗑️
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    );
                  })}
                </div>
                {suggestions.length > 0 && (
                  <button className="btn btn-signal btn-sm" type="button" style={{ marginTop: 6 }} onClick={acceptAll}>
                    Accept all
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Response variants */}
          <div className="panel panel-pad" style={{ marginBottom: 90 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div className="section-title" style={{ marginBottom: 2 }}>Response variants</div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  aria-label="Allow rephrasing"
                  checked={allowRephrasing}
                  onChange={(e) => setAllowRephrasing(e.target.checked)}
                />
                Allow rephrasing
              </label>
            </div>
            <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '4px 0 0' }}>
              When enabled, paraphrased variants are generated automatically on save, so the bot doesn&apos;t repeat itself word-for-word.
            </p>
            {!isCreate && allowRephrasing && variants.length > 0 && (
              <div style={{ marginTop: 14 }}>
                {variants.map((v, idx) => {
                  const isBase = (v.position ?? idx) === 0;
                  return (
                    <div className="variant-row" key={v.id}>
                      <span className="idx">{v.position ?? idx}</span>
                      <textarea
                        aria-label={`Variant ${v.position ?? idx}`}
                        value={v.variant_text}
                        onChange={(e) => editVariantText(v.id, e.target.value)}
                      />
                      <button
                        className="btn btn-ghost btn-sm"
                        type="button"
                        disabled={isBase}
                        title={isBase ? "Base text can't be deleted" : undefined}
                        onClick={() => !isBase && handleDeleteVariant(v.id)}
                      >
                        {isBase ? 'Base' : 'Delete'}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      <div
        style={{ position: 'sticky', bottom: 0, background: 'var(--paper-raised)', borderTop: '1px solid var(--line)', padding: '14px 28px', display: 'flex', gap: 8, justifyContent: 'flex-end' }}
      >
        <button className="btn btn-outline" type="button" onClick={() => router.push('/admin/intents')}>
          Cancel
        </button>
        <button className="btn btn-primary" type="button" onClick={handleSave} disabled={saving}>
          {saving && <span className="spinner" style={{ borderTopColor: 'var(--text-inv)' }} />}
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>
    </main>
  );
}
