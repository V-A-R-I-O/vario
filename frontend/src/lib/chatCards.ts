// Which card a bot reply renders as (slice-33, ADR-006).
//
// The role pack's `card` is authoritative. Replies from the pre-Rasa (v1) packs
// carry no card, so a transitional adapter derives one from the *live* turn;
// otherwise the reply is plain text (or a FAQ answer for FAQ intents).
import type { BotMessageData, KeyValue, Option } from '@/components/chat/types';
import { createHRLeaveBalanceMessage } from '@/components/chat/HRLeaveBalanceCard';
import {
  createITTicketNotFoundMessage,
  createITTicketStatusMessage,
} from '@/components/chat/ITTicketStatusCard';
import { createAdmissionsFeeDeadlineMessage } from '@/components/chat/AdmissionsFeeDeadlineCard';

// Must match rasa-shared/contract/card-types.json.
export const CARD_TYPES = [
  'plain_text',
  'data_card',
  'slot_prompt',
  'confirmation',
  'result',
  'not_found',
  'faq_answer',
  'error',
  'list',
] as const;

// What the Confirm / Cancel buttons send (ADR-006 §3).
export const CONFIRM_TEXT = 'confirm';
export const CANCEL_TEXT = 'cancel';

export interface SessionSnapshot {
  current_form?: string | null;
  current_step?: string | null;
  slots?: Record<string, any> | null;
}

export interface BotReply {
  content: string;
  intent_name?: string | null;
  card?: unknown;
  // Only present on a live turn (from /api/chat); history has no session.
  session?: SessionSnapshot | null;
}

export function asCard(card: unknown): BotMessageData | null {
  if (card && typeof card === 'object' && (CARD_TYPES as readonly string[]).includes((card as any).type)) {
    return card as BotMessageData;
  }
  return null;
}

export function isFaqIntent(intent?: string | null): boolean {
  return Boolean(intent && intent.startsWith('ask_') && (intent.includes('policy') || intent.includes('faq')));
}

export function cardForReply(reply: BotReply): BotMessageData {
  return (
    asCard(reply.card) ??
    legacyCard(reply) ??
    (isFaqIntent(reply.intent_name)
      ? { type: 'faq_answer', text: reply.content }
      : { type: 'plain_text', text: reply.content })
  );
}

// Attach the UI behaviour a server card can't carry: what buttons send, and
// whether they're still clickable.
export function withActions(
  card: BotMessageData,
  { send, disabled }: { send: (text: string) => void; disabled: boolean }
): BotMessageData {
  if (card.type === 'slot_prompt') {
    return { ...card, disabled, onSelect: send };
  }
  if (card.type === 'confirmation') {
    return { ...card, disabled, onConfirm: () => send(CONFIRM_TEXT), onCancel: () => send(CANCEL_TEXT) };
  }
  return card;
}

// --- Transitional: cards for the pre-Rasa (v1) role packs -------------------
// v1 packs return their whole accumulated state in `slots`, so every rule here
// is gated on this turn's intent *and* form/step — leftovers from an earlier
// workflow can't produce a card. Delete this block once slices 35/37/39 replace
// the v1 packs (ADR-006 §8).

const LEAVE_TYPES: Option[] = [
  { label: 'Casual', value: 'casual' },
  { label: 'Sick', value: 'sick' },
  { label: 'Earned', value: 'earned' },
];
const TICKET_CATEGORIES: Option[] = ['Hardware', 'Software', 'Access', 'Network', 'Other'].map((label) => ({
  label,
  value: label.toLowerCase(),
}));
const PROGRAMS: Option[] = ['Computer Science (B.Tech)', 'Data Science (M.Tech)', 'MBA'].map((label) => ({
  label,
  value: label,
}));

const isNumeric = (v: unknown) => v !== null && v !== undefined && v !== '' && !Number.isNaN(Number(v));
const listOf = (v: unknown) => (Array.isArray(v) ? v : []);

function confirmation(title: string, rows: KeyValue[]): BotMessageData {
  return { type: 'confirmation', title, rows, confirmLabel: 'Confirm', cancelLabel: 'Cancel' };
}

export function legacyCard(reply: BotReply): BotMessageData | null {
  if (!reply.session) return null;
  const s = reply.session.slots ?? {};
  const form = reply.session.current_form ?? null;
  const step = reply.session.current_step ?? null;

  switch (reply.intent_name) {
    case 'check_leave_balance':
      if (!form && [s.total, s.casual, s.sick, s.earned].every(isNumeric)) {
        return createHRLeaveBalanceMessage({
          total: Number(s.total),
          casual: Number(s.casual),
          sick: Number(s.sick),
          earned: Number(s.earned),
        });
      }
      return null;

    case 'submit_leave_request':
      if (form && step === 'leave_type') {
        return { type: 'slot_prompt', text: 'What type of leave would you like to request?', options: LEAVE_TYPES };
      }
      if (form && s.confirmation_pending && s.leave_type && s.start_date && s.end_date) {
        return confirmation('Confirm Leave Request', [
          { label: 'Leave Type', value: String(s.leave_type) },
          { label: 'Start Date', value: String(s.start_date) },
          { label: 'End Date', value: String(s.end_date) },
          { label: 'Reason', value: String(s.reason || 'N/A') },
        ]);
      }
      // The reply names the new reference ID; an older one left in slots won't match.
      if (!form && s.reference_id && reply.content.includes(String(s.reference_id))) {
        return { type: 'result', text: 'Leave request submitted successfully! Reference ID:', referenceId: String(s.reference_id) };
      }
      return null;

    case 'raise_ticket':
      if (form && step === 'ask_category') {
        return { type: 'slot_prompt', text: reply.content, options: TICKET_CATEGORIES };
      }
      if (form && step === 'confirm' && s.category && s.description) {
        return confirmation('Confirm IT Support Ticket', [
          { label: 'Category', value: String(s.category) },
          { label: 'Description', value: String(s.description) },
          { label: 'Reporter', value: String(s.reporter || 'Authenticated user') },
        ]);
      }
      if (!form && s.ticket_result && s.ticket_id) {
        return {
          type: 'result',
          text: s.ticket_reused
            ? 'This matches a ticket you just created. Reusing existing ticket:'
            : 'Ticket created successfully. Reference ID:',
          referenceId: String(s.ticket_id),
        };
      }
      return null;

    case 'check_ticket_status':
      if (form || !s.ticket_id) return null;
      if (s.found === false) return createITTicketNotFoundMessage(String(s.ticket_id));
      if (s.found === true && s.status) {
        return createITTicketStatusMessage({
          ticketId: String(s.ticket_id),
          status: String(s.status),
          category: s.category,
          description: s.description,
          reporter: s.reporter,
          updatedAt: s.updated_at,
        });
      }
      return null;

    case 'reset_password':
      if (form) return null;
      if (s.reset_result && s.employee_id) {
        return { type: 'result', text: reply.content, referenceId: String(s.employee_id) };
      }
      if (s.reset_denied) return { type: 'error', text: reply.content };
      return null;

    case 'check_application_status': {
      if (form || !s.application_id) return null;
      if (s.found === false) return { type: 'not_found', text: reply.content };
      if (!s.status || !s.next_step) return null;
      const rows: KeyValue[] = [
        { label: 'Application ID', value: String(s.application_id) },
        { label: 'Status', value: String(s.status) },
        { label: 'Next Step', value: String(s.next_step) },
      ];
      if (s.applicant_name) rows.push({ label: 'Applicant', value: String(s.applicant_name) });
      if (s.program) rows.push({ label: 'Program', value: String(s.program) });
      if (s.fee_status) rows.push({ label: 'Fee Status', value: String(s.fee_status) });
      return { type: 'data_card', title: `Application ${s.application_id} Status`, rows };
    }

    case 'get_document_checklist':
      if (form) return { type: 'slot_prompt', text: reply.content, options: PROGRAMS };
      if (s.found === false) return { type: 'not_found', text: reply.content };
      if (listOf(s.required_documents).length > 0) {
        return {
          type: 'list',
          title: `${s.program || 'Admission'} Required Documents:`,
          ordered: true,
          items: listOf(s.required_documents).map(String),
        };
      }
      return null;

    case 'ask_fee_deadline':
      if (form) return null;
      return createAdmissionsFeeDeadlineMessage({
        academicYear: s.academic_year,
        fees: listOf(s.fees),
        deadlines: listOf(s.deadlines),
        refundPolicy: s.refund_policy,
        text: reply.content,
      });

    default:
      return null;
  }
}
