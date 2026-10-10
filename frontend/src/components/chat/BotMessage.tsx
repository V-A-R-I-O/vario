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
      return <SlotPrompt text={message.text} options={message.options} onSelect={message.onSelect} />;
    case 'confirmation':
      return (
        <Confirmation
          title={message.title}
          rows={message.rows}
          confirmLabel={message.confirmLabel}
          cancelLabel={message.cancelLabel}
          onConfirm={message.onConfirm}
          onCancel={message.onCancel}
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

// Full chat-thread row: bot avatar + message content, left-aligned.
export function BotMessage({ message }: { message: BotMessageData }) {
  return (
    <div className="msg-row bot">
      <BotAvatar />
      <BotMessageContent message={message} />
    </div>
  );
}

// User message row: right-aligned bubble with initials avatar.
export function UserMessage({ text, initials = 'You' }: { text: string; initials?: string }) {
  return (
    <div className="msg-row user">
      <div className="avatar-user">{initials}</div>
      <div className="bubble user">{text}</div>
    </div>
  );
}
