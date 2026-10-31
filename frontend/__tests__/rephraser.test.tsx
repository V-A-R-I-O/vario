import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { IntentEditor } from '../src/components/admin/IntentEditor';
import * as api from '../src/lib/api';

jest.mock('../src/lib/api');
const mockedApi = api as jest.Mocked<typeof api>;

const mockRouter = { push: jest.fn(), replace: jest.fn() };
jest.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
  usePathname: () => '/admin/intents/i1',
}));

function makeToken(role: string, email = 'anita.rao@acme.com') {
  return `h.${btoa(JSON.stringify({ sub: 'admin-1', role, email }))}.s`;
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.setItem('vario_token', makeToken('hr_admin'));
});

const mockIntentWithVariants = {
  id: 'i1',
  name: 'check_leave_balance',
  intent_type: 'dynamic_workflow' as const,
  needs_retrain: false,
  updated_at: '2026-09-07T10:00:00Z',
  training_phrases: [
    { id: 'p1', phrase_text: "What's my leave balance?" },
    { id: 'p2', phrase_text: 'How many leaves do I have left?' },
  ],
  response_template: {
    id: 't1',
    template_key: 'check_leave_balance_response',
    base_text: 'You have {balance} days of leave remaining.',
    allow_rephrasing: true,
    available_variables: ['balance'],
    variants: [
      { id: 'v0', variant_text: 'You have {balance} days of leave remaining.', position: 0 },
      { id: 'v1', variant_text: 'Your current leave balance is {balance} days.', position: 1 },
      { id: 'v2', variant_text: 'As of today, you have {balance} days of leave.', position: 2 },
    ],
  },
};

describe('Rephraser UI — Generate Similar review flow', () => {
  beforeEach(() => {
    mockedApi.fetchIntents.mockResolvedValue({
      status: 'success',
      data: { role_pack: 'hr', intents: [mockIntentWithVariants] },
    });
  });

  it('allows accepting, editing, and rejecting generated suggestions', async () => {
    mockedApi.generatePhrases.mockResolvedValue({
      status: 'success',
      data: {
        intent_id: 'i1',
        generated_phrases: [
          'Can I check my leave count?',
          'Tell me my time off days',
          'Show remaining vacation',
        ],
      },
    });

    render(<IntentEditor intentId="i1" />);
    await screen.findByLabelText('System key');

    // Click Generate similar
    fireEvent.click(screen.getByRole('button', { name: /Generate similar/i }));
    await waitFor(() => expect(mockedApi.generatePhrases).toHaveBeenCalledWith('i1'));

    // Verify all 3 suggestions appear
    expect(await screen.findByText('Can I check my leave count?')).toBeInTheDocument();
    expect(screen.getByText('Tell me my time off days')).toBeInTheDocument();
    expect(screen.getByText('Show remaining vacation')).toBeInTheDocument();

    // 1. Accept first suggestion
    fireEvent.click(screen.getByRole('button', { name: 'Accept Can I check my leave count?' }));
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Accept Can I check my leave count?' })).toBeNull()
    );
    // It should now be in the training phrases list
    expect(screen.getByText('Can I check my leave count?')).toBeInTheDocument();

    // 2. Edit second suggestion
    fireEvent.click(screen.getByRole('button', { name: 'Edit Tell me my time off days' }));
    const editInput = screen.getByLabelText('Edit phrase Tell me my time off days');
    expect(editInput).toBeInTheDocument();
    fireEvent.change(editInput, { target: { value: 'Tell me my remaining vacation days' } });
    // Click Accept edited
    fireEvent.click(screen.getByRole('button', { name: 'Accept Tell me my time off days' }));
    await waitFor(() =>
      expect(screen.queryByLabelText('Edit phrase Tell me my time off days')).toBeNull()
    );
    expect(screen.getByText('Tell me my remaining vacation days')).toBeInTheDocument();

    // 3. Reject third suggestion
    fireEvent.click(screen.getByRole('button', { name: 'Reject Show remaining vacation' }));
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Reject Show remaining vacation' })).toBeNull()
    );
    expect(screen.queryByText('Show remaining vacation')).toBeNull();
  });

  it('supports Accept All to accept all remaining suggestions', async () => {
    mockedApi.generatePhrases.mockResolvedValue({
      status: 'success',
      data: {
        intent_id: 'i1',
        generated_phrases: ['Phrase A', 'Phrase B'],
      },
    });

    render(<IntentEditor intentId="i1" />);
    await screen.findByLabelText('System key');

    fireEvent.click(screen.getByRole('button', { name: /Generate similar/i }));
    await screen.findByText('Phrase A');

    fireEvent.click(screen.getByRole('button', { name: /Accept all/i }));
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: /Accept all/i })).toBeNull()
    );
    // Both phrases should be added to the training phrases
    expect(screen.getByText('Phrase A')).toBeInTheDocument();
    expect(screen.getByText('Phrase B')).toBeInTheDocument();
  });
});

describe('Rephraser UI — Response Variants review and edit', () => {
  beforeEach(() => {
    mockedApi.fetchIntents.mockResolvedValue({
      status: 'success',
      data: { role_pack: 'hr', intents: [mockIntentWithVariants] },
    });
  });

  it('renders base variant and generated variants, protects base from deletion', async () => {
    mockedApi.deleteVariant.mockResolvedValue({
      status: 'success',
      data: { deleted_variant_id: 'v1' },
    });

    render(<IntentEditor intentId="i1" />);
    await screen.findByLabelText('System key');

    // Check all variants rendered
    expect(screen.getByLabelText('Variant 0')).toHaveValue('You have {balance} days of leave remaining.');
    expect(screen.getByLabelText('Variant 1')).toHaveValue('Your current leave balance is {balance} days.');
    expect(screen.getByLabelText('Variant 2')).toHaveValue('As of today, you have {balance} days of leave.');

    // Base button is disabled
    const baseBtn = screen.getByRole('button', { name: 'Base' });
    expect(baseBtn).toBeDisabled();

    // Delete variant 1
    const deleteBtns = screen.getAllByRole('button', { name: 'Delete' });
    fireEvent.click(deleteBtns[0]);
    await waitFor(() => expect(mockedApi.deleteVariant).toHaveBeenCalledWith('v1'));
  });
});
