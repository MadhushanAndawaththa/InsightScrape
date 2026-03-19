import { describe, it, expect, vi, beforeEach } from 'vitest';
import { runAudit, checkHealth, API_URL } from '../api/audit';

// Mock global fetch
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

describe('API module', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('API_URL', () => {
    it('defaults to localhost:8000', () => {
      expect(API_URL).toBe('http://localhost:8000/api');
    });
  });

  describe('checkHealth', () => {
    it('returns true when API is healthy', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      const result = await checkHealth();
      expect(result).toBe(true);
    });

    it('returns false when API is down', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));
      const result = await checkHealth();
      expect(result).toBe(false);
    });

    it('returns false when response is not ok', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      const result = await checkHealth();
      expect(result).toBe(false);
    });
  });

  describe('runAudit', () => {
    it('sends POST request with URL', async () => {
      const mockResult = { url: 'https://test.com', metrics: {} };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResult),
      });

      const result = await runAudit('https://test.com');
      expect(result).toEqual(mockResult);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/audit',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: 'https://test.com' }),
        }),
      );
    });

    it('throws error with detail message on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'Page not found' }),
      });

      await expect(runAudit('https://bad.com')).rejects.toThrow('Page not found');
    });

    it('throws generic error when no detail in response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.reject(new Error('parse error')),
      });

      await expect(runAudit('https://bad.com')).rejects.toThrow('Audit failed');
    });
  });
});
