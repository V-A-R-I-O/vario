// Generic renderer: given a BotMessageData payload, render the matching
// component. This is the single entry point role packs use to turn a
// structured bot response into UI.
import React from 'react';
import type { BotMessageData } from './types';
import {
  Confirmation,
  DataCard,
  ErrorCard,
  FaqAnswer,
  ListCard,
  NotFound,
  PlainText,
  Result,
  SlotPrompt,
} from './messages';

export function BotMessageContent({ message }: { message: BotMessageData }) {
  switch (message.type) {
    case 'plain_text':
      return <PlainText text={message.text} />;
    case 'data_card':
      return <DataCard title={message.title} rows={message.rows} />;
    case 'slot_prompt':
      return (
        <SlotPrompt
          text={message.text}
          options={message.options}
          onSelect={message.onSelect}
          disabled={message.disabled}
        />
      );
    case 'confirmation':
      return (
        <Confirmation
          title={message.title}
          rows={message.rows}
          confirmLabel={message.confirmLabel}
          cancelLabel={message.cancelLabel}
          onConfirm={message.onConfirm}
          onCancel={message.onCancel}
          disabled={message.disabled}
        />
      );
    case 'result':
      return <Result text={message.text} referenceId={message.referenceId} />;
    case 'not_found':
      return <NotFound text={message.text} />;
    case 'faq_answer':
      return <FaqAnswer text={message.text} />;
    case 'error':
      return <ErrorCard text={message.text} />;
    case 'list':
      return <ListCard title={message.title} ordered={message.ordered} items={message.items} />;
    default: {
      // Exhaustiveness guard — a new type must be handled above.
      const _never: never = message;
      return null;
    }
  }
}

function BotAvatar() {
  return (
    <div className="avatar-bot">
      <svg viewBox="0 0 24 24" fill="none">
        <path
          d="M3 12h2.2l1.8-5 3 10 2.6-8 1.6 4.4h2.4l1.8-3.4 1.6 2h2"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

// Speaker button that replays a bot reply's audio in talk mode (slice-06).
function ReplayButton({ onReplay }: { onReplay: () => void }) {
  return (
    <button
      className="icon-btn btn-sm"
      type="button"
      style={{ width: 26, height: 26, flex: 'none' }}
      title="Replay audio"
      aria-label="Replay audio"
      onClick={onReplay}
    >
      <svg viewBox="0 0 24 24" fill="none" style={{ width: 12, height: 12 }}>
        <path
          d="M11 5 6 9H3v6h3l5 4V5ZM16 8a5 5 0 0 1 0 8"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </button>
  );
}

// Full chat-thread row: bot avatar + message content, left-aligned. In talk mode
// an optional `onReplay` adds a speaker button that replays the reply's audio.
export function BotMessage({
  message,
  onReplay,
}: {
  message: BotMessageData;
  onReplay?: () => void;
}) {
  return (
    <div className="msg-row bot">
      <BotAvatar />
      <BotMessageContent message={message} />
      {onReplay && <ReplayButton onReplay={onReplay} />}
    </div>
  );
}

// User message row: right-aligned bubble with initials avatar. A message that
// failed to send shows a "Not sent" note with a Retry button.
export function UserMessage({
  text,
  initials = 'You',
  failed = false,
  onRetry,
}: {
  text: string;
  initials?: string;
  failed?: boolean;
  onRetry?: () => void;
}) {
  return (
    <>
      <div className="msg-row user">
        <div className="avatar-user">{initials}</div>
        <div className="bubble user" style={failed ? { opacity: 0.6 } : undefined}>{text}</div>
      </div>
      {failed && (
        <div
          className="msg-failed"
          style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--danger)' }}
        >
          Not sent
          {onRetry && (
            <button className="btn btn-outline btn-sm" type="button" onClick={onRetry}>
              Retry
            </button>
          )}
        </div>
      )}
    </>
  );
}
