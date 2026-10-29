// Tells the sidebar to reload its conversation list after a conversation is
// created or gets a new message (slice-33).

export const CONVERSATIONS_CHANGED = 'vario:conversations-changed';

export function notifyConversationsChanged(): void {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(CONVERSATIONS_CHANGED));
  }
}

// Subscribe; returns the unsubscribe function.
export function onConversationsChanged(listener: () => void): () => void {
  window.addEventListener(CONVERSATIONS_CHANGED, listener);
  return () => window.removeEventListener(CONVERSATIONS_CHANGED, listener);
}
