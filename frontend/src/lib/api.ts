const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type GetTokenFn = () => Promise<string | null>;

/**
 * Authenticated fetch wrapper that injects a Clerk Bearer token.
 *
 * @param path  - API path (e.g. "/api/agent/chat/stream")
 * @param getToken - `getToken` from Clerk's `useAuth()` hook
 * @param options  - Standard `RequestInit` overrides
 */
export async function apiFetch(
  path: string,
  getToken: GetTokenFn,
  options: RequestInit = {},
): Promise<Response> {
  const token = await getToken();

  const headers = new Headers(options.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  // Cache-bust to prevent browsers from reusing stale 307 redirects
  const separator = path.includes("?") ? "&" : "?";
  const url = `${API_BASE}${path}${separator}_t=${Date.now()}`;

  return fetch(url, {
    ...options,
    headers,
  });
}
