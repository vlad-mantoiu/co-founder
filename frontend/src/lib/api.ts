type GetTokenFn = () => Promise<string | null>;

/**
 * Authenticated fetch wrapper that injects a Clerk Bearer token.
 *
 * Requests are proxied through Next.js rewrites (/backend/:path* → backend)
 * to avoid CORS. The path should start with /api/ (e.g. "/api/projects").
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

  // Route through Next.js rewrite proxy to avoid CORS
  // /api/projects → /backend/api/projects → (rewrite) → backend:8000/api/projects
  const url = `/backend${path}`;

  return fetch(url, {
    ...options,
    headers,
  });
}
