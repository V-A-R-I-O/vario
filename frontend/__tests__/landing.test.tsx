import { render, screen, fireEvent } from '@testing-library/react';
import LandingPage from '../src/app/page';

describe('VARIO Public Landing Page', () => {
  it('renders without requiring authentication', () => {
    render(<LandingPage />);
    expect(screen.getAllByText('VARIO').length).toBeGreaterThan(0);
  });

  it('immediately communicates VARIO branding and project name', () => {
    render(<LandingPage />);
    // Project full name
    expect(
      screen.getAllByText(/Voice Adaptive Role & Intent Orchestrator/i).length
    ).toBeGreaterThan(0);
    // Value proposition headline
    expect(
      screen.getByRole('heading', {
        name: /One Voice Assistant Brain.*Pluggable Roles.*for Every Department/i,
      })
    ).toBeInTheDocument();
  });

  it('renders primary and secondary calls to action in hero', () => {
    render(<LandingPage />);
    // Primary CTA to enter application
    const enterAppLinks = screen.getAllByRole('link', { name: /enter application/i });
    expect(enterAppLinks.length).toBeGreaterThan(0);
    expect(enterAppLinks[0]).toHaveAttribute('href', '/login');

    // Secondary CTA to GitHub
    const githubLinks = screen.getAllByRole('link', { name: /view on github/i });
    expect(githubLinks.length).toBeGreaterThan(0);
    expect(githubLinks[0]).toHaveAttribute('href', 'https://github.com/V-A-R-I-O/vario');

    // Documentation CTA
    const docLinks = screen.getAllByRole('link', { name: /architecture docs/i });
    expect(docLinks.length).toBeGreaterThan(0);
    expect(docLinks[0]).toHaveAttribute('href', '#architecture');
  });

  it('explains the complete voice/text → intent → role → service flow', () => {
    render(<LandingPage />);
    // Verify each step in the core workflow pipeline
    expect(screen.getByRole('heading', { name: /^User$/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^Voice \/ Text$/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^Intent \+ Context$/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^Role-aware Orchestration$/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^Role Pack$/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^Enterprise Service$/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^Response$/i })).toBeInTheDocument();
  });

  it('represents HR, IT Support, and Admissions use cases', () => {
    render(<LandingPage />);
    // Role headings
    expect(screen.getByRole('heading', { name: /^HR Self-Service$/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^IT Support$/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /^Admissions$/i })).toBeInTheDocument();

    // Specific workflows represented
    expect(screen.getByText(/Leave Balance Inquiries/i)).toBeInTheDocument();
    expect(screen.getByText(/Guided Leave Application/i)).toBeInTheDocument();
    expect(screen.getByText(/Automated Ticket Creation/i)).toBeInTheDocument();
    expect(screen.getByText(/Guided Password Reset/i)).toBeInTheDocument();
    expect(screen.getByText(/Application Status Lookup/i)).toBeInTheDocument();
    expect(screen.getByText(/Program Document Checklists/i)).toBeInTheDocument();
  });

  it('explains the architecture at a high level across major layers', () => {
    render(<LandingPage />);
    // Layers
    expect(screen.getByRole('heading', { name: /Frontend Client/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /API Gateway/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Core Orchestration/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Role Packs/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Integration Adapters/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Mock Enterprise Services/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /PostgreSQL Database/i })).toBeInTheDocument();
  });

  it('renders functional GitHub and documentation links', () => {
    render(<LandingPage />);
    const githubLink = screen.getAllByRole('link', { name: /github/i })[0];
    expect(githubLink).toHaveAttribute('href', expect.stringContaining('github.com/V-A-R-I-O/vario'));

    const docLinks = screen.getAllByRole('link', { name: /documentation/i });
    expect(docLinks.length).toBeGreaterThan(0);
  });

  it('represents Apache License 2.0 information', () => {
    render(<LandingPage />);
    expect(screen.getAllByText(/Apache License 2\.0/i).length).toBeGreaterThan(0);
    const licenseLinks = screen.getAllByRole('link', { name: /license/i });
    expect(licenseLinks.length).toBeGreaterThan(0);
  });

  it('allows interactive role switching in the hero simulation', () => {
    render(<LandingPage />);
    // Initial selection is HR
    expect(screen.getByText(/hr_leave_balance/i)).toBeInTheDocument();

    // Switch to IT Support
    const itRoleButtons = screen.getAllByRole('button', { name: /it support/i });
    fireEvent.click(itRoleButtons[0]);
    expect(screen.getByText(/it_password_reset/i)).toBeInTheDocument();

    // Switch to Admissions
    const admRoleButtons = screen.getAllByRole('button', { name: /admissions/i });
    fireEvent.click(admRoleButtons[0]);
    expect(screen.getByText(/adm_application_status/i)).toBeInTheDocument();
  });
});
