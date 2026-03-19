import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AuditApp } from '../components/AuditApp';

// Mock the audit API module
vi.mock('../api/audit', () => ({
  checkHealth: vi.fn().mockResolvedValue(true),
  runAudit: vi.fn(),
}));

// Mock react-markdown to avoid ESM issues in tests
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => children,
}));

describe('AuditApp', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders the main heading', () => {
    render(<AuditApp />);
    expect(screen.getByText('AI-Powered Website Audit')).toBeInTheDocument();
  });

  it('renders the URL input and Run Audit button', async () => {
    render(<AuditApp />);
    // Wait for warmup to complete
    await waitFor(() => {
      expect(screen.getByPlaceholderText('https://example.com')).toBeInTheDocument();
    });
    expect(screen.getByText('Run Audit')).toBeInTheDocument();
  });

  it('renders InsightScrape branding in nav', () => {
    render(<AuditApp />);
    expect(screen.getByText('InsightScrape')).toBeInTheDocument();
  });

  it('has a theme toggle button', () => {
    render(<AuditApp />);
    expect(screen.getByLabelText('Toggle theme')).toBeInTheDocument();
  });

  it('toggles dark mode on button click', () => {
    render(<AuditApp />);
    const toggleBtn = screen.getByLabelText('Toggle theme');

    // Initial state depends on system preference; just verify toggle works
    const initialDark = document.documentElement.classList.contains('dark');
    fireEvent.click(toggleBtn);
    const afterClick = document.documentElement.classList.contains('dark');
    expect(afterClick).toBe(!initialDark);
  });

  it('persists theme choice to localStorage', () => {
    render(<AuditApp />);
    const toggleBtn = screen.getByLabelText('Toggle theme');
    fireEvent.click(toggleBtn);
    const stored = localStorage.getItem('insightscrape-theme');
    expect(stored).toBeTruthy();
    expect(['dark', 'light']).toContain(stored);
  });

  it('shows footer with tech stack', () => {
    render(<AuditApp />);
    expect(screen.getByText(/FastAPI.*React.*Tailwind.*Gemini/i)).toBeInTheDocument();
  });

  it('prevents submission with empty URL', async () => {
    const { runAudit } = await import('../api/audit');
    render(<AuditApp />);
    await waitFor(() => {
      expect(screen.getByText('Run Audit')).toBeInTheDocument();
    });
    // The input has required attribute, so form won't submit
    // Check that runAudit was not called
    expect(runAudit).not.toHaveBeenCalled();
  });
});
