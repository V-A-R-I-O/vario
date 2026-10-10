export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

export async function loginUser(email: string, password: string) {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || 'Login failed');
  }
  return data;
}

import { getToken } from './auth';

async function authFetch(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };
  
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  
  const data = await res.json();
  if (!res.ok) {
    if (res.status === 401 && typeof window !== 'undefined') {
        localStorage.removeItem('vario_token');
        window.location.href = '/login';
    }
    throw new Error(data.error || 'Request failed');
  }
  return data;
}

export async function fetchConversations(role_pack?: string, status?: string) {
  const params = new URLSearchParams();
  if (role_pack) params.append('role_pack', role_pack);
  if (status) params.append('status', status);
  const q = params.toString();
  return authFetch(`/conversations${q ? `?${q}` : ''}`);
}

export async function createConversation(role_pack: string, title?: string) {
  return authFetch(`/conversations`, {
    method: 'POST',
    body: JSON.stringify({ role_pack, title }),
  });
}

export async function fetchMessages(conversationId: string) {
  return authFetch(`/conversations/${conversationId}/messages`);
}

export async function sendChatMessage(
  conversationId: string,
  message: string,
  mode: 'chat' | 'talk' = 'chat'
) {
  return authFetch(`/chat`, {
    method: 'POST',
    body: JSON.stringify({ conversation_id: conversationId, message, mode }),
  });
}
