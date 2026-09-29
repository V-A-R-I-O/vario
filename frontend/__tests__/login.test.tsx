import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LoginForm from '../src/components/LoginForm';

// Mock the router
const pushMock = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

// Mock the API client
const mockLoginUser = jest.fn();
jest.mock('../src/lib/api', () => ({
  loginUser: (...args: any[]) => mockLoginUser(...args),
}));

describe('LoginForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders all elements correctly', () => {
    render(<LoginForm />);
    expect(screen.getByText('V.A.R.I.O.')).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument();
    expect(screen.getByText(/forgot your password/i)).toBeInTheDocument();
  });

  it('submitting valid credentials shows loading state and redirects', async () => {
    mockLoginUser.mockResolvedValueOnce({
      status: 'success',
      data: { token: 'fake-jwt-token' }
    });

    render(<LoginForm />);
    
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /log in/i });

    await userEvent.type(emailInput, 'test@org.example.com');
    await userEvent.type(passwordInput, 'password123');
    
    fireEvent.click(submitButton);

    expect(submitButton).toHaveTextContent(/logging in/i);
    expect(submitButton).toBeDisabled();

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith('/home');
    });
  });

  it('submitting invalid credentials shows error message', async () => {
    mockLoginUser.mockRejectedValueOnce(new Error('Invalid email or password'));

    render(<LoginForm />);
    
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitButton = screen.getByRole('button', { name: /log in/i });

    await userEvent.type(emailInput, 'wrong@org.example.com');
    await userEvent.type(passwordInput, 'badpass');
    
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Invalid email or password')).toBeInTheDocument();
    });
    
    // Ensure button is re-enabled
    expect(submitButton).not.toBeDisabled();
    expect(submitButton).toHaveTextContent('Log in');
  });
});
