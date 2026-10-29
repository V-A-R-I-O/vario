import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ConversationLogsPage from '../src/app/admin/conversation-logs/page';
import * as api from '../src/lib/api';

jest.mock('../src/lib/api');
const mockedApi = api as jest.Mocked<typeof api>;

const mockRouter = { push: jest.fn(), replace: jest.fn() };
const mockPathname = { value: '/admin/conversation-logs' };
jest.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
  usePathname: () => mockPathname.value,
}));

function makeToken(role: string, email = 'anita.rao@acme.com') {
  const payload = btoa(JSON.stringify({ sub: 'admin-1', role, email }));
  return `h.${payload}.s`;
}

beforeEach(() => {
  jest.clearAllMocks();
  mockPathname.value = '/admin/conversation-logs';
  localStorage.setItem('vario_token', makeToken('hr_admin'));
});

describe('Conversation Logs page (slice-11)', () => {
  const mockConversations: api.AdminConversationItem[] = [
    {
      id: 'conv-1',
      user_name: 'Priya Nair',
      user_email: 'priya.nair@acme-corp.com',
      title: 'Leave request',
      message_count: 8,
      last_intent: 'submit_leave_request',
      started_at: '2026-09-09T09:12:00Z',
      last_message_at: '2026-09-09T09:15:00Z',
    },
    {
      id: 'conv-2',
      user_name: 'Rohan Mehta',
      user_email: 'rohan.mehta@acme-corp.com',
      title: 'Leave balance inquiry',
      message_count: 5,
      last_intent: 'check_leave_balance',
      started_at: '2026-09-08T15:58:00Z',
      last_message_at: '2026-09-08T16:02:00Z',
    },
  ];

  const mockTranscript: api.AdminTranscriptData = {
    conversation_id: 'conv-1',
    role_pack: 'hr',
    user_name: 'Priya Nair',
    messages: [
      {
        id: 'm-1',
        sender: 'bot',
        content: "Hi Priya! I'm the HR assistant. What would you like to do?",
        intent_name: 'greet',
        confidence: 0.98,
        entities: null,
        created_at: '2026-09-09T09:12:05Z',
      },
      {
        id: 'm-2',
        sender: 'user',
        content: "What's my leave balance?",
        intent_name: null,
        confidence: null,
        entities: null,
        created_at: '2026-09-09T09:12:30Z',
      },
      {
        id: 'm-3',
        sender: 'bot',
        content: 'Leave balance: Casual 5 · Sick 4 · Earned 3',
        intent_name: 'check_leave_balance',
        confidence: 0.94,
        entities: null,
        created_at: '2026-09-09T09:12:32Z',
      },
    ],
  };

  it('renders conversations list with user info, count, and last intent', async () => {
    mockedApi.fetchAdminConversations.mockResolvedValue({
      status: 'success',
      data: { role_pack: 'hr', total: 2, conversations: mockConversations },
    });

    render(<ConversationLogsPage />);

    expect(screen.getByTestId('conversations-skeleton')).toBeInTheDocument();

    await screen.findByText('Priya Nair');
    expect(screen.getByText('priya.nair@acme-corp.com')).toBeInTheDocument();
    expect(screen.getByText('8 msgs')).toBeInTheDocument();
    expect(screen.getByText('submit_leave_request')).toBeInTheDocument();

    expect(screen.getByText('Rohan Mehta')).toBeInTheDocument();
    expect(screen.getByText('rohan.mehta@acme-corp.com')).toBeInTheDocument();
    expect(screen.getByText('5 msgs')).toBeInTheDocument();
    expect(screen.getByText('check_leave_balance')).toBeInTheDocument();

    expect(screen.getByText(/1–2 of 2/i)).toBeInTheDocument();
  });

  it('expands a conversation row to display the full read-only transcript with intent and confidence', async () => {
    mockedApi.fetchAdminConversations.mockResolvedValue({
      status: 'success',
      data: { role_pack: 'hr', total: 2, conversations: mockConversations },
    });
    mockedApi.fetchAdminConversationMessages.mockResolvedValue({
      status: 'success',
      data: mockTranscript,
    });

    render(<ConversationLogsPage />);

    await screen.findByText('Priya Nair');

    const viewButtons = screen.getAllByRole('button', { name: /View transcript/i });
    fireEvent.click(viewButtons[0]);

    await waitFor(() => {
      expect(mockedApi.fetchAdminConversationMessages).toHaveBeenCalledWith('conv-1');
    });

    // Transcript messages are visible
    expect(await screen.findByText("Hi Priya! I'm the HR assistant. What would you like to do?")).toBeInTheDocument();
    expect(screen.getByText("What's my leave balance?")).toBeInTheDocument();
    expect(screen.getByText('Leave balance: Casual 5 · Sick 4 · Earned 3')).toBeInTheDocument();

    // Intent and confidence badges in transcript
    expect(screen.getByText('greet')).toBeInTheDocument();
    expect(screen.getByText(/confidence 0.98/i)).toBeInTheDocument();
    expect(screen.getAllByText('check_leave_balance').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/confidence 0.94/i)).toBeInTheDocument();

    // Read-only badge
    expect(screen.getByText('Read-only')).toBeInTheDocument();

    // Toggle button changes to "Hide transcript"
    expect(screen.getByRole('button', { name: /Hide transcript/i })).toBeInTheDocument();

    // Click again collapses it
    fireEvent.click(screen.getByRole('button', { name: /Hide transcript/i }));
    expect(screen.queryByText("Hi Priya! I'm the HR assistant. What would you like to do?")).not.toBeInTheDocument();
  });

  it('filters by actor and date range', async () => {
    mockedApi.fetchAdminConversations.mockResolvedValue({
      status: 'success',
      data: { role_pack: 'hr', total: 2, conversations: mockConversations },
    });

    render(<ConversationLogsPage />);
    await screen.findByText('Priya Nair');

    const actorInput = screen.getByLabelText(/Search by actor/i);
    const fromInput = screen.getByLabelText(/From date/i);
    const toInput = screen.getByLabelText(/To date/i);
    const applyBtn = screen.getByRole('button', { name: 'Apply' });

    fireEvent.change(actorInput, { target: { value: 'Priya' } });
    fireEvent.change(fromInput, { target: { value: '2026-09-01' } });
    fireEvent.change(toInput, { target: { value: '2026-09-10' } });
    fireEvent.click(applyBtn);

    expect(mockedApi.fetchAdminConversations).toHaveBeenCalledWith(
      expect.objectContaining({
        actor_id: 'Priya',
        from: '2026-09-01',
        to: '2026-09-10',
      })
    );

    // Test clear filters
    const clearBtn = screen.getByRole('button', { name: 'Clear filters' });
    fireEvent.click(clearBtn);

    await waitFor(() => {
      expect(actorInput).toHaveValue('');
      expect(fromInput).toHaveValue('');
      expect(toInput).toHaveValue('');
    });
  });

  it('navigates pagination controls', async () => {
    mockedApi.fetchAdminConversations.mockResolvedValue({
      status: 'success',
      data: { role_pack: 'hr', total: 42, conversations: mockConversations },
    });

    render(<ConversationLogsPage />);
    await screen.findByText('Priya Nair');

    expect(screen.getByText(/1–20 of 42/i)).toBeInTheDocument();
    const prevBtn = screen.getByRole('button', { name: 'Previous' });
    const nextBtn = screen.getByRole('button', { name: 'Next' });

    expect(prevBtn).toBeDisabled();
    expect(nextBtn).not.toBeDisabled();

    fireEvent.click(nextBtn);

    await waitFor(() => {
      expect(mockedApi.fetchAdminConversations).toHaveBeenCalledWith(
        expect.objectContaining({
          offset: 20,
        })
      );
    });
  });

  it('renders the empty state when no conversations exist', async () => {
    mockedApi.fetchAdminConversations.mockResolvedValue({
      status: 'success',
      data: { role_pack: 'hr', total: 0, conversations: [] },
    });

    render(<ConversationLogsPage />);
    await screen.findByText('No conversations yet');
  });

  it('renders the error state and retries on failure', async () => {
    mockedApi.fetchAdminConversations.mockRejectedValueOnce(new Error('Network error'));

    render(<ConversationLogsPage />);
    await screen.findByText(/Couldn't load conversation logs/i);

    mockedApi.fetchAdminConversations.mockResolvedValueOnce({
      status: 'success',
      data: { role_pack: 'hr', total: 2, conversations: mockConversations },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    await screen.findByText('Priya Nair');
  });
});
