import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ChatPage from '../src/app/home/chat/[id]/page';
import * as api from '../src/lib/api';

jest.mock('../src/lib/api');
const mockedApi = api as jest.Mocked<typeof api>;

describe('Slice 16: HR Policy FAQ Chat Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedApi.fetchConversations.mockResolvedValue({
      status: 'success',
      data: {
        conversations: [
          { id: 'c1', role_pack: 'hr', title: 'HR Policy Inquiry' },
        ],
      },
    });
  });

  it('renders policy answer via faq_answer component when asking WFH policy', async () => {
    mockedApi.fetchMessages.mockResolvedValue({
      status: 'success',
      data: { messages: [] },
    });

    mockedApi.sendChatMessage.mockResolvedValue({
      status: 'success',
      data: {
        response_text: 'Employees may work from home up to 3 days per week, subject to manager approval.',
        intent: 'ask_wfh_policy',
        confidence: 0.95,
        entities: {},
        session: {
          current_form: null,
          current_step: null,
          slots: { is_faq: true, intent_type: 'static_faq' },
        },
        tts_available: false,
      },
    });

    render(<ChatPage params={{ id: 'c1' }} />);

    // Wait for initial load to settle
    await screen.findByText(/Ask HR Assistant anything/i);

    const input = screen.getByPlaceholderText(/Message HR Assistant/i);
    fireEvent.change(input, { target: { value: "What's the WFH policy?" } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));

    await waitFor(() => {
      expect(mockedApi.sendChatMessage).toHaveBeenCalledWith('c1', "What's the WFH policy?", 'chat');
    });

    // Verify response is displayed
    const responseEl = await screen.findByText(/Employees may work from home up to 3 days per week/i);
    expect(responseEl).toBeInTheDocument();

    // Verify it is rendered inside a bot-text bubble (FaqAnswer component)
    expect(responseEl.closest('.bot-text')).toBeInTheDocument();
  });

  it('renders preloaded policy FAQ messages from history as faq_answer', async () => {
    mockedApi.fetchMessages.mockResolvedValue({
      status: 'success',
      data: {
        messages: [
          {
            id: 'm1',
            sender: 'user',
            content: "What's the WFH policy?",
            created_at: '2026-10-15T10:00:00Z',
          },
          {
            id: 'm2',
            sender: 'bot',
            content: 'Employees may work from home up to 3 days per week, subject to manager approval.',
            intent_name: 'ask_wfh_policy',
            confidence: 0.95,
            created_at: '2026-10-15T10:00:02Z',
          },
        ],
      },
    });

    render(<ChatPage params={{ id: 'c1' }} />);

    const botMessage = await screen.findByText(/Employees may work from home up to 3 days per week/i);
    expect(botMessage).toBeInTheDocument();
    expect(botMessage.closest('.bot-text')).toBeInTheDocument();
  });
});
