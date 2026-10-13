import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import IntentListPage from '../src/app/admin/intents/page';
import AuditLogPage from '../src/app/admin/audit-log/page';
import * as api from '../src/lib/api';

jest.mock('../src/lib/api');
const mockedApi = api as jest.Mocked<typeof api>;

// Mock Next navigation. The router object must be STABLE across renders (as it
// is in real Next) — a fresh object each render would re-fire useAdmin's effect.
// jest.mock is hoisted, so factory-referenced vars must be `mock`-prefixed.
const mockRouter = { push: jest.fn(), replace: jest.fn() };
const mockPathname = { value: '/admin/intents' };
jest.mock('next/navigation', () => ({
  useRouter: () => mockRouter,
  usePathname: () => mockPathname.value,
}));

// Craft a minimal JWT whose payload decodes to an admin role.
function makeToken(role: string, email = 'anita.rao@acme.com') {
  const payload = btoa(JSON.stringify({ sub: 'admin-1', role, email }));
  return `h.${payload}.s`;
}

beforeEach(() => {
  jest.clearAllMocks();
  mockPathname.value = '/admin/intents';
  localStorage.setItem('vario_token', makeToken('hr_admin'));
});

// --- Intent List framework --------------------------------------------------

describe('Intent List page', () => {
  const intents = [
    { id: 'i1', name: 'check_leave_balance', intent_type: 'dynamic_workflow', needs_retrain: false, updated_at: '2026-08-20T10:00:00Z', training_phrases: [{}, {}] },
    { id: 'i2', name: 'ask_wfh_policy', intent_type: 'static_faq', needs_retrain: true, updated_at: '2026-09-07T10:00:00Z', training_phrases: [{}] },
  ];

  it('renders role-pack intents with type badges, retrain banner, Delete disabled for workflows', async () => {
    mockedApi.fetchIntents.mockResolvedValue({ status: 'success', data: { role_pack: 'hr', intents } });
    render(<IntentListPage />);

    await screen.findByText('check_leave_balance');
    // Role-scoped title from the admin badge.
    expect(screen.getByRole('heading', { name: /HR intents/i })).toBeInTheDocument();
    // Type badges.
    expect(screen.getByText('Dynamic workflow')).toBeInTheDocument();
    expect(screen.getByText('Static FAQ')).toBeInTheDocument();
    // Needs-retrain badge + retrain-status banner.
    expect(screen.getByText('Needs retrain')).toBeInTheDocument();
    expect(screen.getByText(/1 intent have changes since the last training run/i)).toBeInTheDocument();
    // Delete disabled for the dynamic workflow, enabled for the FAQ.
    const deletes = screen.getAllByRole('button', { name: 'Delete' });
    expect(deletes[0]).toBeDisabled(); // workflow row
    expect(deletes[1]).not.toBeDisabled(); // faq row
  });

  it('renders the loading state then resolves', async () => {
    let resolve: (v: any) => void = () => {};
    mockedApi.fetchIntents.mockReturnValue(new Promise((r) => (resolve = r)) as any);
    render(<IntentListPage />);
    expect(screen.getByTestId('intent-skeleton')).toBeInTheDocument();
    resolve({ status: 'success', data: { role_pack: 'hr', intents } });
    await screen.findByText('check_leave_balance');
  });

  it('renders the empty state when there are no intents', async () => {
    mockedApi.fetchIntents.mockResolvedValue({ status: 'success', data: { role_pack: 'hr', intents: [] } });
    render(<IntentListPage />);
    await screen.findByText('No intents configured');
  });

  it('renders the error state when the fetch fails', async () => {
    mockedApi.fetchIntents.mockRejectedValue(new Error('boom'));
    render(<IntentListPage />);
    await screen.findByText(/Couldn.t load intents/i);
  });
});

// --- Audit Log page ---------------------------------------------------------

describe('Audit Log page', () => {
  const entries = [
    { id: 'l1', actor_id: 'u1', actor_name: 'Priya Nair', action_type: 'leave_submitted', reference_id: 'LEAVE-2045', details: { leave_type: 'Casual', days: 2 }, created_at: '2026-09-09T09:14:00Z' },
    { id: 'l2', actor_id: 'u2', actor_name: 'Anita Rao', action_type: 'template_edited', reference_id: 'leave_status_response', details: { field: 'base_text' }, created_at: '2026-09-09T08:40:00Z' },
  ];

  beforeEach(() => {
    mockPathname.value = '/admin/audit-log';
  });

  it('renders filter bar, table, and pagination range', async () => {
    mockedApi.fetchAuditLog.mockResolvedValue({ status: 'success', data: { role_pack: 'hr', total: 42, entries } });
    render(<AuditLogPage />);

    await screen.findByText('Priya Nair');
    // action_type humanized for display in the table cell (also appears as a
    // filter <option>, so scope to the cell role).
    expect(screen.getByRole('cell', { name: 'Leave submitted' })).toBeInTheDocument();
    // Filter bar controls.
    expect(screen.getByLabelText('Filter by action')).toBeInTheDocument();
    expect(screen.getByLabelText('Search by actor')).toBeInTheDocument();
    // Pagination range + Next enabled (42 > page size).
    expect(screen.getByText('1–20 of 42')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Next' })).not.toBeDisabled();
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();
  });

  it('expands a row to show JSONB details on click', async () => {
    mockedApi.fetchAuditLog.mockResolvedValue({ status: 'success', data: { role_pack: 'hr', total: 2, entries } });
    render(<AuditLogPage />);

    const row = await screen.findByText('Priya Nair');
    expect(screen.queryByTestId('detail-l1')).toBeNull();
    fireEvent.click(row);
    expect(screen.getByTestId('detail-l1')).toBeInTheDocument();
    expect(screen.getByText(/"leave_type": "Casual"/)).toBeInTheDocument();
  });

  it('applies the action-type filter in the query', async () => {
    mockedApi.fetchAuditLog.mockResolvedValue({ status: 'success', data: { role_pack: 'hr', total: 2, entries } });
    render(<AuditLogPage />);
    await screen.findByText('Priya Nair');

    fireEvent.change(screen.getByLabelText('Filter by action'), { target: { value: 'template_edited' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }));

    await waitFor(() =>
      expect(mockedApi.fetchAuditLog).toHaveBeenLastCalledWith(
        expect.objectContaining({ action_type: 'template_edited', limit: 20, offset: 0 })
      )
    );
  });

  it('paginates: Next advances the offset', async () => {
    mockedApi.fetchAuditLog.mockResolvedValue({ status: 'success', data: { role_pack: 'hr', total: 42, entries } });
    render(<AuditLogPage />);
    await screen.findByText('Priya Nair');

    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    await waitFor(() =>
      expect(mockedApi.fetchAuditLog).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 20 }))
    );
  });
});
