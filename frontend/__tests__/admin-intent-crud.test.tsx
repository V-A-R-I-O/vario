import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import IntentListPage from '../src/app/admin/intents/page';
import { IntentEditor } from '../src/components/admin/IntentEditor';
import * as api from '../src/lib/api';

jest.mock('../src/lib/api');
const mockedApi = api as jest.Mocked<typeof api>;

const mockRouter = { push: jest.fn(), replace: jest.fn() };
const mockPathname = { value: '/admin/intents' };
jest.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
  usePathname: () => mockPathname.value,
}));

function makeToken(role: string, email = 'anita.rao@acme.com') {
  return `h.${btoa(JSON.stringify({ sub: 'admin-1', role, email }))}.s`;
}

beforeEach(() => {
  jest.clearAllMocks();
  mockPathname.value = '/admin/intents';
  localStorage.setItem('vario_token', makeToken('hr_admin'));
});

const dynamicIntent = {
  id: 'i1',
  name: 'check_leave_status',
  intent_type: 'dynamic_workflow',
  needs_retrain: false,
  updated_at: '2026-08-20T10:00:00Z',
  training_phrases: [{ id: 'p1', phrase_text: "What's my leave status?" }],
  response_template: {
    id: 't1',
    template_key: 'check_leave_status_response',
    base_text: 'Your leave {leave_id} is {status}.',
    allow_rephrasing: true,
    available_variables: ['leave_id', 'status'],
    variants: [
      { id: 'v0', variant_text: 'Your leave {leave_id} is {status}.', position: 0 },
      { id: 'v1', variant_text: 'Leave {leave_id}: {status}.', position: 1 },
    ],
  },
};

const faqIntent = {
  id: 'i2',
  name: 'ask_wfh_policy',
  intent_type: 'static_faq',
  needs_retrain: true,
  updated_at: '2026-09-07T10:00:00Z',
  training_phrases: [{ id: 'p2', phrase_text: 'Can I work from home?' }],
  response_template: {
    id: 't2',
    template_key: 'ask_wfh_policy_response',
    base_text: 'You may WFH 3 days a week.',
    allow_rephrasing: true,
    available_variables: [],
    variants: [{ id: 'v2', variant_text: 'You may WFH 3 days a week.', position: 0 }],
  },
};

// --- Intent List CRUD wiring -----------------------------------------------

describe('Intent List CRUD wiring', () => {
  beforeEach(() => {
    mockedApi.fetchIntents.mockResolvedValue({
      status: 'success',
      data: { role_pack: 'hr', intents: [dynamicIntent, faqIntent] },
    });
  });

  it('navigates to the create page from Add FAQ', async () => {
    render(<IntentListPage />);
    await screen.findByText('check_leave_status');
    fireEvent.click(screen.getByRole('button', { name: /Add FAQ/i }));
    expect(mockRouter.push).toHaveBeenCalledWith('/admin/intents/new');
  });

  it('navigates to the edit page from Edit', async () => {
    render(<IntentListPage />);
    await screen.findByText('check_leave_status');
    fireEvent.click(screen.getAllByRole('button', { name: 'Edit' })[0]);
    expect(mockRouter.push).toHaveBeenCalledWith('/admin/intents/i1');
  });

  it('deletes a static FAQ through the confirm modal', async () => {
    mockedApi.deleteIntent.mockResolvedValue({ status: 'success', data: { deleted_intent_id: 'i2' } });
    render(<IntentListPage />);
    await screen.findByText('ask_wfh_policy');

    // FAQ delete is enabled; workflow delete is disabled.
    const deletes = screen.getAllByRole('button', { name: 'Delete' });
    expect(deletes[0]).toBeDisabled(); // dynamic workflow row
    fireEvent.click(deletes[1]); // static faq row

    await screen.findByText(/Delete .ask_wfh_policy/i);
    fireEvent.click(screen.getByRole('button', { name: 'Delete intent' }));
    await waitFor(() => expect(mockedApi.deleteIntent).toHaveBeenCalledWith('i2'));
  });
});

// --- Editor: Mode B (static FAQ create) ------------------------------------

describe('IntentEditor — Mode B (create FAQ)', () => {
  it('shows a validated name input + variable-free textarea and creates on save', async () => {
    mockedApi.createIntent.mockResolvedValue({ status: 'success', data: { intent: { id: 'new' } } });
    render(<IntentEditor />);

    // Mode B fields present; no System key.
    expect(screen.getByLabelText('Intent name')).toBeInTheDocument();
    expect(screen.getByLabelText('Response template')).toBeInTheDocument();
    expect(screen.queryByLabelText('System key')).toBeNull();

    // Empty name → validation error, no API call.
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByText(/Intent name is required/i)).toBeInTheDocument();
    expect(mockedApi.createIntent).not.toHaveBeenCalled();

    // Fill it in, add a phrase, save.
    fireEvent.change(screen.getByLabelText('Intent name'), { target: { value: 'ask_parking' } });
    fireEvent.change(screen.getByLabelText('Response template'), { target: { value: 'Parking is behind block C.' } });
    fireEvent.change(screen.getByLabelText('Add a training phrase'), { target: { value: 'Where do I park?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() =>
      expect(mockedApi.createIntent).toHaveBeenCalledWith({
        name: 'ask_parking',
        training_phrases: ['Where do I park?'],
        response_template: { base_text: 'Parking is behind block C.', allow_rephrasing: true },
      })
    );
    await waitFor(() => expect(mockRouter.push).toHaveBeenCalledWith('/admin/intents'));
  });
});

// --- Editor: Mode A (dynamic workflow edit) --------------------------------

describe('IntentEditor — Mode A (dynamic workflow)', () => {
  beforeEach(() => {
    mockedApi.fetchIntents.mockResolvedValue({
      status: 'success',
      data: { role_pack: 'hr', intents: [dynamicIntent] },
    });
  });

  it('shows read-only System key, variable chips, and an unknown-variable warning', async () => {
    render(<IntentEditor intentId="i1" />);

    const sysKey = (await screen.findByLabelText('System key')) as HTMLInputElement;
    expect(sysKey).toBeDisabled();
    expect(sysKey.value).toBe('check_leave_status_response');
    // Variable chips.
    expect(screen.getByText('{leave_id}')).toBeInTheDocument();
    expect(screen.getByText('{status}')).toBeInTheDocument();
    // No editable name field in Mode A.
    expect(screen.queryByLabelText('Intent name')).toBeNull();

    // Typing an unlisted placeholder raises the warning.
    expect(screen.queryByText(/Unknown variable/i)).toBeNull();
    fireEvent.change(screen.getByLabelText('Response template'), {
      target: { value: 'Your leave {leave_id} is {bogus}.' },
    });
    expect(await screen.findByText(/Unknown variable \{bogus\}/i)).toBeInTheDocument();
  });

  it('wires Generate Similar to the endpoint and accepts suggestions', async () => {
    mockedApi.generatePhrases.mockResolvedValue({
      status: 'success',
      data: { intent_id: 'i1', generated_phrases: ['Is my leave approved?', 'Track my leave'] },
    });
    render(<IntentEditor intentId="i1" />);
    await screen.findByLabelText('System key');

    fireEvent.click(screen.getByRole('button', { name: /Generate similar/i }));
    await waitFor(() => expect(mockedApi.generatePhrases).toHaveBeenCalledWith('i1'));

    const suggestion = await screen.findByText('Is my leave approved?');
    expect(suggestion).toBeInTheDocument();
    // Accept it → moves into the training-phrase list.
    fireEvent.click(screen.getByRole('button', { name: 'Accept Is my leave approved?' }));
    // The accepted suggestion leaves the suggestion list.
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Accept Is my leave approved?' })).toBeNull()
    );
  });
});
