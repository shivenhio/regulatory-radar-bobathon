/**
 * Thin REST client wrapper.
 *
 * Mock mode (default): when `VITE_API_BASE_URL` is not set, all api/* modules
 * return mock JSON from `src/lib/mock/*`. To wire your live backend, set
 * `VITE_API_BASE_URL=https://your-backend.example.com` and uncomment the
 * `client.get(...)` calls inside each api/* file.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined;

export const isMockMode = !BASE_URL;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!BASE_URL) {
    throw new Error(
      `API call to ${path} attempted but VITE_API_BASE_URL is not set. Either set it or keep using the mock data path.`,
    );
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} — ${path}`);
  }
  return (await res.json()) as T;
}

export const client = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
};

/** Simulate latency in mock mode so loading states are visible. */
export function mockDelay<T>(value: T, ms = 120): Promise<T> {
  return new Promise((r) => setTimeout(() => r(value), ms));
}
