// Slice-33 (SCRUM-43): chat UI hardening. Bot replies are shaped like the
// ADR-006 contract fixtures in rasa-shared/contract/.
import fs from 'fs';
import path from 'path';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import ChatPage from '../src/app/home/chat/[id]/page';
import HomeLayout from '../src/app/home/layout';
import NewConversationPage from '../src/app/home/new/page';
import * as api from '../src/lib/api';
import { ApiError } from '../src/lib/apiError';
import { CARD_TYPES } from '../src/lib/chatCards';
import { CONVERSATIONS_CHANGED, notifyConversationsChanged } from '../src/lib/conversationEvents';

jest.mock('../src/lib/api');
const mockedApi = api as jest.Mocked<typeof api>;

const mockPush = jest.fn();
// Stable like Next's real router; a new object per render would re-run effects forever.
const mockRouter = { push: mockPush };
jest.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
}));

const CONTRACT_DIR = path.join(__dirname, '..', '..', 'rasa-shared', 'contract');
const contract = (name: string) => JSON.parse(fs.readFileSync(path.join(CONTRACT_DIR, name), 'utf-8'));

// Shape a converse reply (gateway ← Rasa) into what /api/chat returns.
function chatReply(fixture: string | null, overrides: Record<string, any> = {}) {
  const base = fixture ? contract(fixture) : { intent: null, confidence: 0.9, entities: {}, slots: {}, current_form: null, current_step: null, response_text: '', card: null };
  const r = { ...base, ...overrides };
  return {
    status: 'success',
    data: {
      response_text: r.response_text,
      intent: r.intent,
      confidence: r.confidence,
      entities: r.entities ?? {},
      session: { current_form: r.current_form ?? null, current_step: r.current_step ?? null, slots: r.slots ?? {} },
      card: r.card ?? null,
      degraded: r.degraded ?? false,
      tts_available: null,
    },
  };
}

const CONFIRM_LEAVE_CARD = {
  type: 'confirmation',
  title: 'Confirm Leave Request',
  rows: [
    { label: 'Leave Type', value: 'sick' },
    { label: 'Start Date', value: '2026-11-10' },
  ],
};

function conversation(role_pack: string) {
  mockedApi.fetchConversations.mockResolvedValue({
    status: 'success',
    data: { conversations: [{ id: 'c1', role_pack, title: 'Test conversation' }] },
  });
}

function history(messages: any[] = []) {
  mockedApi.fetchMessages.mockResolvedValue({ status: 'success', data: { conversation_id: 'c1', messages } });
}

async function openChat() {
  render(<ChatPage params={{ id: 'c1' }} />);
  await waitFor(() => expect(mockedApi.fetchMessages).toHaveBeenCalled());
  await waitFor(() => expect(screen.getByRole('button', { name: 'Send' })).not.toBeDisabled());
}

async function send(text: string) {
  fireEvent.change(screen.getByRole('textbox'), { target: { value: text } });
  fireEvent.click(screen.getByRole('button', { name: 'Send' }));
  await waitFor(() => expect(mockedApi.sendChatMessage).toHaveBeenCalledWith('c1', text, 'chat'));
}

class FakeRecognition {
  static last: FakeRecognition | null = null;
  lang = '';
  interimResults = false;
  continuous = false;
  onresult: ((e: any) => void) | null = null;
  onend: (() => void) | null = null;
  onerror: ((e: any) => void) | null = null;
  start = jest.fn();
  stop = jest.fn();
  abort = jest.fn();
  constructor() {
    FakeRecognition.last = this;
  }
  say(text: string) {
    this.onresult?.({ results: [{ 0: { transcript: text }, isFinal: true }] });
    this.onend?.();
  }
}

beforeEach(() => {
  // resetAllMocks (not clear) so a failed test can't leak queued replies into the next.
  jest.resetAllMocks();
  localStorage.clear();
  history();
  conversation('hr');
  (window as any).SpeechRecognition = FakeRecognition;
  (window as any).webkitSpeechRecognition = FakeRecognition;
  Object.defineProperty(window, 'isSecureContext', { value: true, configurable: true });
});

test('card types match the shared ADR-006 contract', () => {
  expect([...CARD_TYPES].sort()).toEqual(contract('card-types.json').sort());
});

describe('cards come from each reply, not from leftover slots', () => {
  test('HR: a balance check does not hijack the WFH answer, prompts and confirmation (ADR-006 cards)', async () => {
    await openChat();
    const balance = chatReply('converse-response-card-turn.json');
    mockedApi.sendChatMessage
      .mockResolvedValueOnce(balance)
      .mockResolvedValueOnce(
        chatReply(null, {
          intent: 'ask_wfh_policy',
          response_text: 'Employees may work from home up to 3 days per week.',
          slots: balance.data.session.slots, // a v1 pack would still be echoing these
        })
      )
      .mockResolvedValueOnce(chatReply('converse-response-form-turn.json'))
      .mockResolvedValueOnce(chatReply('converse-response-form-turn.json', { current_step: null, card: CONFIRM_LEAVE_CARD, response_text: 'Please confirm.' }));

    await send("What's my leave balance?");
    await screen.findByText('Your leave balance');
    await send('can I work from home?');
    expect(await screen.findByText(/work from home up to 3 days/)).toHaveClass('bot-text');
    await send('I want to apply for leave');
    await screen.findByRole('button', { name: 'Annual' });
    await send('sick');
    await screen.findByText('Confirm Leave Request');

    expect(screen.getAllByText('Your leave balance')).toHaveLength(1);
    expect(screen.getByRole('button', { name: 'Confirm' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeEnabled();
  });

  test('HR: the same sequence from a pre-Rasa pack (no card, slots echoed every turn)', async () => {
    await openChat();
    const leftovers = { total: 22, casual: 4, sick: 6, earned: 12 };
    mockedApi.sendChatMessage
      .mockResolvedValueOnce(chatReply(null, { intent: 'check_leave_balance', response_text: 'Your leave balance: 22 days.', slots: leftovers }))
      .mockResolvedValueOnce(chatReply(null, { intent: 'ask_wfh_policy', response_text: 'WFH is allowed 3 days a week.', slots: { ...leftovers, is_faq: true } }))
      .mockResolvedValueOnce(
        chatReply(null, {
          intent: 'submit_leave_request',
          response_text: 'Review your request.',
          current_form: 'submit_leave_request',
          slots: { ...leftovers, leave_type: 'sick', start_date: '2026-11-10', end_date: '2026-11-12', reason: 'fever', confirmation_pending: true },
        })
      );

    await send('leave balance');
    await screen.findByText('Your Leave Balance');
    await send('wfh?');
    expect(await screen.findByText('WFH is allowed 3 days a week.')).toHaveClass('bot-text');
    await send('confirm my leave');
    await screen.findByText('Confirm Leave Request');
    expect(screen.getAllByText('Your Leave Balance')).toHaveLength(1);
    expect(screen.getByRole('button', { name: 'Confirm' })).toBeEnabled();
  });

  test('Admissions: a status lookup after a checklist renders as a status card', async () => {
    conversation('admissions');
    await openChat();
    const checklist = { type: 'list', title: 'MBA Required Documents:', ordered: true, items: ['SOP', 'Degree certificate'] };
    const status = {
      type: 'data_card',
      title: 'Application APP-1001 Status',
      rows: [{ label: 'Status', value: 'Under Review' }],
    };
    mockedApi.sendChatMessage
      .mockResolvedValueOnce(chatReply(null, { intent: 'get_document_checklist', response_text: 'Here are the MBA documents.', card: checklist }))
      .mockResolvedValueOnce(chatReply(null, { intent: 'check_application_status', response_text: 'APP-1001 is Under Review.', card: status, slots: { required_documents: ['SOP'] } }));

    await send('documents for MBA');
    await screen.findByText('MBA Required Documents:');
    await send('status of APP-1001');
    await screen.findByText('Application APP-1001 Status');
    expect(screen.getAllByText('MBA Required Documents:')).toHaveLength(1);
  });

  test('Admissions (pre-Rasa pack): status after checklist is a status card, not the old list', async () => {
    conversation('admissions');
    await openChat();
    const docs = { program: 'MBA', required_documents: ['SOP', 'Degree certificate'] };
    mockedApi.sendChatMessage
      .mockResolvedValueOnce(chatReply(null, { intent: 'get_document_checklist', response_text: 'MBA documents.', slots: docs }))
      .mockResolvedValueOnce(
        chatReply(null, {
          intent: 'check_application_status',
          response_text: 'APP-1001 is Under Review.',
          slots: { ...docs, application_id: 'APP-1001', status: 'Under Review', next_step: 'Await decision.', found: true },
        })
      );

    await send('documents for MBA');
    await screen.findByText('MBA Required Documents:');
    await send('status of APP-1001');
    await screen.findByText('Application APP-1001 Status');
    expect(screen.getAllByText('MBA Required Documents:')).toHaveLength(1);
  });

  test('a degraded reply renders as an error card', async () => {
    await openChat();
    const text = 'The HR assistant is unavailable right now. Please try again in a moment.';
    mockedApi.sendChatMessage.mockResolvedValueOnce(chatReply(null, { response_text: text, card: { type: 'error', text }, degraded: true }));
    await send('hello');
    expect((await screen.findByText(text)).closest('.error-card')).toBeInTheDocument();
  });

  test('IT (pre-Rasa pack): asking for a ticket ID after a lookup shows the prompt, not the old ticket', async () => {
    conversation('it');
    await openChat();
    const lookup = { ticket_id: 'IT-1001', status: 'In Progress', found: true, category: 'hardware' };
    mockedApi.sendChatMessage
      .mockResolvedValueOnce(chatReply(null, { intent: 'check_ticket_status', response_text: 'IT-1001 is In Progress.', slots: lookup }))
      .mockResolvedValueOnce(
        chatReply(null, {
          intent: 'check_ticket_status',
          response_text: 'Please provide your ticket ID (for example, TKT-1234).',
          current_form: 'check_ticket_status_form',
          current_step: 'await_ticket_id',
          slots: lookup,
        })
      );

    await send('status of IT-1001');
    await screen.findByText('IT-1001');
    await send('can you check ticket status for me');
    expect(await screen.findByText(/Please provide your ticket ID/)).toHaveClass('bot-text');
    expect(screen.getAllByText('IT-1001')).toHaveLength(1);
    expect(screen.queryByText('TKT-1234')).not.toBeInTheDocument();
  });
});

describe('reload', () => {
  test('cards stored with messages render the same after a reload', async () => {
    const balanceCard = contract('converse-response-card-turn.json').card;
    history([
      { id: 'm1', sender: 'user', content: 'balance?', card: null },
      { id: 'm2', sender: 'bot', content: 'You have 22 days.', intent_name: 'check_leave_balance', card: balanceCard },
      { id: 'm3', sender: 'user', content: 'leave', card: null },
      { id: 'm4', sender: 'bot', content: 'Please confirm.', intent_name: 'submit_leave_request', card: CONFIRM_LEAVE_CARD },
    ]);
    await openChat();
    expect(screen.getByText('Your leave balance')).toBeInTheDocument();
    expect(screen.getByText('22 days')).toBeInTheDocument();
    expect(screen.getByText('Confirm Leave Request')).toBeInTheDocument();
  });

  test('a pre-Rasa checklist reply without a stored card reloads as plain text, not a program prompt', async () => {
    conversation('admissions');
    history([{ id: 'm1', sender: 'bot', content: 'Required documents for MBA: SOP, Degree.', intent_name: 'get_document_checklist' }]);
    await openChat();
    expect(screen.getByText('Required documents for MBA: SOP, Degree.')).toHaveClass('bot-text');
    expect(screen.queryByRole('button', { name: 'MBA' })).not.toBeInTheDocument();
  });
});

describe('buttons', () => {
  test('a double-click on Confirm sends exactly one message', async () => {
    history([{ id: 'm1', sender: 'bot', content: 'Please confirm.', intent_name: 'submit_leave_request', card: CONFIRM_LEAVE_CARD }]);
    let resolveSend: (v: any) => void = () => {};
    mockedApi.sendChatMessage.mockImplementation(() => new Promise((resolve) => { resolveSend = resolve; }));
    await openChat();

    const confirm = screen.getByRole('button', { name: 'Confirm' });
    fireEvent.click(confirm);
    fireEvent.click(confirm);

    expect(mockedApi.sendChatMessage).toHaveBeenCalledTimes(1);
    expect(mockedApi.sendChatMessage).toHaveBeenCalledWith('c1', 'confirm', 'chat');
    await act(async () => resolveSend(chatReply(null, { response_text: 'Submitted.' })));
  });

  test('a prompt that was already answered is no longer clickable', async () => {
    history([
      { id: 'm1', sender: 'bot', content: 'Which type?', card: contract('converse-response-form-turn.json').card },
      { id: 'm2', sender: 'user', content: 'sick' },
      { id: 'm3', sender: 'bot', content: 'When does it start?' },
    ]);
    await openChat();
    expect(screen.getByRole('button', { name: 'Sick' })).toBeDisabled();
  });
});

describe('send errors', () => {
  test('a 429 tells the user to wait, and the failed message can be retried', async () => {
    await openChat();
    mockedApi.sendChatMessage
      .mockRejectedValueOnce(new ApiError(429, 'Rate limit exceeded. Try again in 30 seconds.'))
      .mockResolvedValueOnce(chatReply(null, { response_text: 'Here you go.' }));

    await send('hello');
    expect(await screen.findByRole('alert')).toHaveTextContent(/too quickly.*wait/i);
    expect(screen.getByText('Not sent')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    await screen.findByText('Here you go.');
    expect(mockedApi.sendChatMessage).toHaveBeenCalledTimes(2);
    expect(screen.queryByText('Not sent')).not.toBeInTheDocument();
    expect(screen.getAllByText('hello')).toHaveLength(1);
  });

  test('a backend that is down is reported as unavailable', async () => {
    await openChat();
    mockedApi.sendChatMessage.mockRejectedValueOnce(new ApiError(0, 'Network request failed'));
    await send('hello');
    expect(await screen.findByRole('alert')).toHaveTextContent(/unavailable/i);
  });

  test('a server error is reported as our fault, not a lost connection', async () => {
    await openChat();
    mockedApi.sendChatMessage.mockRejectedValueOnce(new ApiError(500, 'Internal server error'));
    await send('hello');
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/went wrong on our side/i);
    expect(alert).not.toHaveTextContent(/connection lost/i);
  });
});

describe('talk mode', () => {
  test('on an insecure page the mic explains it needs HTTPS instead of opening a stuck overlay', async () => {
    Object.defineProperty(window, 'isSecureContext', { value: false, configurable: true });
    await openChat();
    fireEvent.click(screen.getByRole('button', { name: 'Talk mode' }));
    expect(await screen.findByText(/Voice needs HTTPS or localhost/)).toBeInTheDocument();
    expect(screen.queryByRole('dialog', { name: 'Talk mode' })).not.toBeInTheDocument();
  });

  test('a speech-recognition error closes the overlay with a message', async () => {
    await openChat();
    fireEvent.click(screen.getByRole('button', { name: 'Talk mode' }));
    expect(screen.getByRole('dialog', { name: 'Talk mode' })).toBeInTheDocument();
    await act(async () => {
      FakeRecognition.last!.onerror?.({ error: 'not-allowed' });
      FakeRecognition.last!.onend?.();
    });
    expect(screen.queryByRole('dialog', { name: 'Talk mode' })).not.toBeInTheDocument();
    expect(screen.getByText(/Microphone access was blocked/)).toBeInTheDocument();
  });

  test('a failed send in talk mode closes the overlay with a message', async () => {
    await openChat();
    mockedApi.sendChatMessage.mockRejectedValueOnce(new ApiError(0, 'Network request failed'));
    fireEvent.click(screen.getByRole('button', { name: 'Talk mode' }));
    await act(async () => {
      FakeRecognition.last!.say('what is my balance');
    });
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Talk mode' })).not.toBeInTheDocument());
    expect(screen.getByText(/couldn't be sent, so talk mode was turned off/)).toBeInTheDocument();
  });

  test('silence closes the overlay instead of leaving it on "Listening…"', async () => {
    await openChat();
    fireEvent.click(screen.getByRole('button', { name: 'Talk mode' }));
    await act(async () => {
      FakeRecognition.last!.onend?.();
    });
    expect(screen.queryByRole('dialog', { name: 'Talk mode' })).not.toBeInTheDocument();
    expect(screen.getByText(/didn't catch anything/)).toBeInTheDocument();
  });
});

describe('sidebar and navigation', () => {
  const token = (role: string) => `h.${btoa(JSON.stringify({ sub: 'u1', role, email: 'someone@org.example.com' }))}.s`;

  test('a new conversation appears in the sidebar without a reload', async () => {
    localStorage.setItem('vario_token', token('end_user'));
    mockedApi.fetchConversations.mockResolvedValueOnce({ status: 'success', data: { conversations: [] } });
    render(<HomeLayout><div /></HomeLayout>);
    await screen.findByText('No conversations yet.');

    mockedApi.fetchConversations.mockResolvedValueOnce({
      status: 'success',
      data: { conversations: [{ id: 'c9', role_pack: 'it', title: 'Laptop issue', last_message_preview: 'hi', last_message_at: '2026-10-29T10:00:00Z' }] },
    });
    act(() => notifyConversationsChanged());
    await screen.findByText('Laptop issue');
  });

  test('sending a message tells the sidebar to refresh', async () => {
    const listener = jest.fn();
    window.addEventListener(CONVERSATIONS_CHANGED, listener);
    await openChat();
    mockedApi.sendChatMessage.mockResolvedValueOnce(chatReply(null, { response_text: 'Hi!' }));
    await send('hello');
    await screen.findByText('Hi!');
    expect(listener).toHaveBeenCalled();
    window.removeEventListener(CONVERSATIONS_CHANGED, listener);
  });

  test('a double-click on a department creates one conversation and refreshes the sidebar', async () => {
    const listener = jest.fn();
    window.addEventListener(CONVERSATIONS_CHANGED, listener);
    let resolveCreate: (v: any) => void = () => {};
    mockedApi.createConversation.mockImplementation(() => new Promise((resolve) => { resolveCreate = resolve; }));
    render(<NewConversationPage />);

    const hr = screen.getByRole('button', { name: /Leave balance, leave requests/ });
    fireEvent.click(hr);
    fireEvent.click(hr);
    expect(mockedApi.createConversation).toHaveBeenCalledTimes(1);

    await act(async () => resolveCreate({ status: 'success', data: { id: 'c2' } }));
    expect(mockPush).toHaveBeenCalledWith('/home/chat/c2');
    expect(listener).toHaveBeenCalled();
    window.removeEventListener(CONVERSATIONS_CHANGED, listener);
  });

  test('admins get a link to the admin console', async () => {
    localStorage.setItem('vario_token', token('hr_admin'));
    mockedApi.fetchConversations.mockResolvedValue({ status: 'success', data: { conversations: [] } });
    render(<HomeLayout><div /></HomeLayout>);
    expect(await screen.findByRole('link', { name: 'Admin console' })).toHaveAttribute('href', '/admin');
  });

  test('employees do not see the admin link', async () => {
    localStorage.setItem('vario_token', token('end_user'));
    mockedApi.fetchConversations.mockResolvedValue({ status: 'success', data: { conversations: [] } });
    render(<HomeLayout><div /></HomeLayout>);
    await screen.findByText('No conversations yet.');
    expect(screen.queryByRole('link', { name: 'Admin console' })).not.toBeInTheDocument();
  });
});
