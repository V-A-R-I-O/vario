// Typed API failures so the UI can tell a rate limit from an outage (slice-33).
// Kept out of lib/api.ts so tests that auto-mock the API client still get the
// real class.

export class ApiError extends Error {
  // HTTP status, or 0 when the request never reached the server.
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export type SendErrorKind = 'rate_limited' | 'unavailable' | 'server' | 'rejected';

export function sendErrorKind(err: unknown): SendErrorKind {
  if (!(err instanceof ApiError) || err.status === 0) return 'unavailable';
  if (err.status === 429) return 'rate_limited';
  if (err.status === 502 || err.status === 503 || err.status === 504) return 'unavailable';
  if (err.status >= 500) return 'server';
  return 'rejected';
}

export const SEND_ERROR_TEXT: Record<SendErrorKind, string> = {
  rate_limited: "You're sending messages too quickly. Please wait a few seconds, then retry.",
  unavailable: 'VARIO is unavailable right now. Check your connection, or try again in a moment.',
  server: 'Something went wrong on our side. Please try again.',
  rejected: "That message couldn't be sent. Please try again.",
};
