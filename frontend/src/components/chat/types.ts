// Shared bot-message type contract for the chat component library.
// These 9 types mirror docs/mockups/ui-reference.md §4 ("Bot message types").
// Role packs (HR / IT / Admissions) compose these generic, props-driven
// components — they are never role-specific.

export interface KeyValue {
  label: string;
  value: string;
}

export interface Option {
  label: string;
  value?: string;
}

export interface PlainTextMessage {
  type: 'plain_text';
  text: string;
}

export interface DataCardMessage {
  type: 'data_card';
  title?: string;
  rows: KeyValue[];
}

export interface SlotPromptMessage {
  type: 'slot_prompt';
  text: string;
  options: Option[];
  onSelect?: (value: string) => void;
}

export interface ConfirmationMessage {
  type: 'confirmation';
  title?: string;
  rows: KeyValue[];
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm?: () => void;
  onCancel?: () => void;
}

export interface ResultMessage {
  type: 'result';
  text: string;
  referenceId?: string;
}

export interface NotFoundMessage {
  type: 'not_found';
  text: string;
}

export interface FaqAnswerMessage {
  type: 'faq_answer';
  text: string;
}

export interface ErrorMessage {
  type: 'error';
  text: string;
}

export interface ListMessage {
  type: 'list';
  title?: string;
  ordered?: boolean;
  items: string[];
}

export type BotMessageData =
  | PlainTextMessage
  | DataCardMessage
  | SlotPromptMessage
  | ConfirmationMessage
  | ResultMessage
  | NotFoundMessage
  | FaqAnswerMessage
  | ErrorMessage
  | ListMessage;

export type BotMessageType = BotMessageData['type'];
