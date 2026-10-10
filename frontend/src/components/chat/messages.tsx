// The 9 bot message components. Each is generic and props-driven; role packs
// supply the data. Styling reuses the VARIO design-system classes defined in
// src/app/mockup.css (ported from docs/mockups/04-chat-view.html).
import React from 'react';
import type {
  ConfirmationMessage,
  DataCardMessage,
  ErrorMessage,
  FaqAnswerMessage,
  ListMessage,
  NotFoundMessage,
  PlainTextMessage,
  ResultMessage,
  SlotPromptMessage,
} from './types';

function KeyValueRows({ rows }: { rows: { label: string; value: string }[] }) {
  return (
    <div className="card-body">
      {rows.map((row, i) => (
        <div className="kv-row" key={i}>
          <span className="k">{row.label}</span>
          <span className="v">{row.value}</span>
        </div>
      ))}
    </div>
  );
}

export function PlainText({ text }: Omit<PlainTextMessage, 'type'>) {
  return <div className="bubble bot-text">{text}</div>;
}

export function DataCard({ title, rows }: Omit<DataCardMessage, 'type'>) {
  return (
    <div className="card-msg">
      {title && <div className="card-head">{title}</div>}
      <KeyValueRows rows={rows} />
    </div>
  );
}

export function SlotPrompt({ text, options, onSelect }: Omit<SlotPromptMessage, 'type'>) {
  return (
    <div className="card-msg">
      <div className="card-body" style={{ paddingTop: 14 }}>{text}</div>
      <div className="opt-row">
        {options.map((opt, i) => (
          <button
            className="opt-btn"
            key={i}
            type="button"
            onClick={() => onSelect?.(opt.value ?? opt.label)}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function Confirmation({
  title,
  rows,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
}: Omit<ConfirmationMessage, 'type'>) {
  return (
    <div className="card-msg">
      {title && <div className="card-head">{title}</div>}
      <KeyValueRows rows={rows} />
      <div className="confirm-actions">
        <button className="btn btn-primary btn-sm" type="button" onClick={onConfirm}>
          {confirmLabel}
        </button>
        <button className="btn btn-outline btn-sm" type="button" onClick={onCancel}>
          {cancelLabel}
        </button>
      </div>
    </div>
  );
}

export function Result({ text, referenceId }: Omit<ResultMessage, 'type'>) {
  return (
    <div className="result-card">
      <svg viewBox="0 0 24 24" fill="none" style={{ width: 17, height: 17, color: 'var(--success)', flex: 'none', marginTop: 1 }}>
        <path d="M20 6 9 17l-5-5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div>
        {text}
        {referenceId && <> <span className="ref">{referenceId}</span></>}
      </div>
    </div>
  );
}

export function NotFound({ text }: Omit<NotFoundMessage, 'type'>) {
  return (
    <div className="warn-card">
      <svg viewBox="0 0 24 24" fill="none" style={{ width: 17, height: 17, color: 'var(--warn)', flex: 'none', marginTop: 1 }}>
        <path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      </svg>
      <div>{text}</div>
    </div>
  );
}

export function FaqAnswer({ text }: Omit<FaqAnswerMessage, 'type'>) {
  return <div className="bubble bot-text" style={{ maxWidth: 360 }}>{text}</div>;
}

export function ErrorCard({ text }: Omit<ErrorMessage, 'type'>) {
  return (
    <div className="error-card">
      <svg viewBox="0 0 24 24" fill="none" style={{ width: 17, height: 17, color: 'var(--danger)', flex: 'none', marginTop: 1 }}>
        <path d="M12 8v5M12 16h.01M12 3 2 21h20L12 3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      </svg>
      <div>{text}</div>
    </div>
  );
}

export function ListCard({ title, ordered = true, items }: Omit<ListMessage, 'type'>) {
  const ListTag = ordered ? 'ol' : 'ul';
  return (
    <div className="list-card">
      {title && <div style={{ fontSize: 13.5, fontWeight: 700 }}>{title}</div>}
      <ListTag>
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ListTag>
    </div>
  );
}
