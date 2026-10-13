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

// --- Admin console (slice-07) ---------------------------------------------

// Intent list framework data (endpoint built in slice-08; scoped to the
// admin's role pack by the backend).
export async function fetchIntents() {
  return authFetch(`/admin/intents`);
}

export interface AuditLogFilters {
  action_type?: string;
  actor_id?: string;
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}

export async function fetchAuditLog(filters: AuditLogFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') params.append(k, String(v));
  });
  const q = params.toString();
  return authFetch(`/admin/audit-log${q ? `?${q}` : ''}`);
}

// --- Admin intent/template/variant CRUD (slice-08) ------------------------

export interface IntentCreatePayload {
  name: string;
  training_phrases: string[];
  response_template: { base_text: string; allow_rephrasing: boolean };
}

export async function createIntent(payload: IntentCreatePayload) {
  return authFetch(`/admin/intents`, { method: 'POST', body: JSON.stringify(payload) });
}

export interface IntentUpdatePayload {
  name?: string;
  training_phrases?: { add?: string[]; remove?: string[] };
}

export async function updateIntent(id: string, payload: IntentUpdatePayload) {
  return authFetch(`/admin/intents/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
}

export async function deleteIntent(id: string) {
  return authFetch(`/admin/intents/${id}`, { method: 'DELETE' });
}

export async function updateTemplate(
  id: string,
  payload: { base_text?: string; allow_rephrasing?: boolean }
) {
  return authFetch(`/admin/templates/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
}

export async function updateVariant(id: string, variant_text: string) {
  return authFetch(`/admin/variants/${id}`, { method: 'PUT', body: JSON.stringify({ variant_text }) });
}

export async function deleteVariant(id: string) {
  return authFetch(`/admin/variants/${id}`, { method: 'DELETE' });
}

export async function generatePhrases(intentId: string, count = 8) {
  return authFetch(`/admin/intents/${intentId}/generate-phrases`, {
    method: 'POST',
    body: JSON.stringify({ count }),
  });
}
