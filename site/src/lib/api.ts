import { API_URL } from './config';

export interface Streamer {
  twitch_user_id: string;
  twitch_login: string;
  display_name: string;
  minecraft_player: string;
  enabled: boolean;
  bridge_connected: boolean;
  minecraft_connected: boolean;
  email_verified: boolean;
  linked: boolean;
}

export interface EventConfig {
  id: number;
  event_number: number;
  action: string;
  enabled: number;
  cooldown: number;
  params: string;
  display_name: string;
}

let csrfToken: string | null = null;

async function fetchCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken;
  const res = await fetch(`${API_URL}/api/csrf-token`, { credentials: "include" });
  if (!res.ok) throw new Error("Failed to fetch CSRF token");
  const data = await res.json();
  csrfToken = data.csrf_token;
  return csrfToken!;
}

function invalidateCsrf() {
  csrfToken = null;
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}${path}`;
  const method = (options.method || "GET").toUpperCase();

  const headers: Record<string, string> = {
    ...((options.headers as Record<string, string>) || {}),
  };

  if (method !== "GET") {
    headers["X-CSRF-Token"] = await fetchCsrfToken();
  }
  if (options.body) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(url, {
    ...options,
    credentials: "include",
    headers,
  });

  if (res.status === 403) {
    invalidateCsrf();
    throw new Error("CSRF token invalid or expired");
  }
  if (res.status === 401 || res.status === 302) {
    throw new Error("NOT_AUTHENTICATED");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `API error ${res.status}`);
  }
  return res.json();
}

export async function getMe(): Promise<Streamer> {
  return apiFetch<Streamer>("/api/me");
}

export async function getSettings(): Promise<{
  minecraft_player: string;
  enabled: boolean;
  events: EventConfig[];
}> {
  return apiFetch("/api/settings");
}

export async function getEvents(): Promise<EventConfig[]> {
  return apiFetch<EventConfig[]>("/api/events");
}

export async function updateEvent(
  eventNumber: number,
  data: Partial<EventConfig>
): Promise<void> {
  await apiFetch(`/api/events/${eventNumber}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function batchUpdateEvents(
  events: { event_number: number; enabled?: boolean; cooldown?: number }[]
): Promise<void> {
  await apiFetch("/api/events/batch", {
    method: "PUT",
    body: JSON.stringify({ events }),
  });
}

export async function logout(): Promise<void> {
  await apiFetch("/api/logout", { method: "POST" });
}

export async function sendVerification(): Promise<void> {
  await apiFetch("/api/email/send", { method: "POST" });
}

export async function getEmailStatus(): Promise<{ verified: boolean; email: string | null }> {
  return apiFetch("/api/email/status");
}

export async function confirmEmail(token: string): Promise<void> {
  await apiFetch("/api/email/confirm", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export async function startLink(): Promise<{ link_code: string; expires_at: string }> {
  return apiFetch("/api/link/start", { method: "POST" });
}

export async function getLinkStatus(): Promise<{ linked: boolean; bridge_instance_id?: string; linked_at?: string }> {
  return apiFetch("/api/link/status");
}

export async function revokeLink(): Promise<void> {
  await apiFetch("/api/link/revoke", { method: "POST" });
}
