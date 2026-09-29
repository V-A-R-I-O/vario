export function storeToken(token: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('vario_token', token);
  }
}

export function getToken() {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('vario_token');
  }
  return null;
}

export function clearToken() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('vario_token');
  }
}
