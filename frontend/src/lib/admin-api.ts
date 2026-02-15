import { apiFetch } from "@/lib/api";

type GetTokenFn = () => Promise<string | null>;

// ---------- Plan Tiers ----------

export interface PlanTier {
  id: number;
  slug: string;
  name: string;
  price_monthly_cents: number;
  price_yearly_cents: number;
  max_projects: number;
  max_sessions_per_day: number;
  max_tokens_per_day: number;
  default_models: Record<string, string>;
  allowed_models: string[];
}

export async function fetchPlans(getToken: GetTokenFn): Promise<PlanTier[]> {
  const res = await apiFetch("/api/admin/plans", getToken);
  if (!res.ok) throw new Error(`Failed to fetch plans: ${res.status}`);
  return res.json();
}

export async function updatePlan(
  planId: number,
  data: Partial<PlanTier>,
  getToken: GetTokenFn,
): Promise<PlanTier> {
  const res = await apiFetch(`/api/admin/plans/${planId}`, getToken, {
    method: "PUT",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update plan: ${res.status}`);
  return res.json();
}

// ---------- Users ----------

export interface UserSummary {
  clerk_user_id: string;
  plan_slug: string;
  is_admin: boolean;
  is_suspended: boolean;
  daily_tokens_used: number;
  created_at: string;
}

export interface UserDetail {
  clerk_user_id: string;
  plan_tier: PlanTier;
  override_models: Record<string, string> | null;
  override_max_projects: number | null;
  override_max_sessions_per_day: number | null;
  override_max_tokens_per_day: number | null;
  is_admin: boolean;
  is_suspended: boolean;
  daily_tokens_used: number;
  created_at: string;
  updated_at: string;
}

export interface UserUpdate {
  plan_tier_slug?: string;
  override_models?: Record<string, string> | null;
  override_max_projects?: number | null;
  override_max_sessions_per_day?: number | null;
  override_max_tokens_per_day?: number | null;
  is_admin?: boolean;
  is_suspended?: boolean;
}

export async function fetchUsers(
  getToken: GetTokenFn,
  params?: { page?: number; per_page?: number; search?: string },
): Promise<UserSummary[]> {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.per_page) query.set("per_page", String(params.per_page));
  if (params?.search) query.set("search", params.search);

  const res = await apiFetch(`/api/admin/users?${query}`, getToken);
  if (!res.ok) throw new Error(`Failed to fetch users: ${res.status}`);
  return res.json();
}

export async function fetchUser(
  clerkId: string,
  getToken: GetTokenFn,
): Promise<UserDetail> {
  const res = await apiFetch(`/api/admin/users/${clerkId}`, getToken);
  if (!res.ok) throw new Error(`Failed to fetch user: ${res.status}`);
  return res.json();
}

export async function updateUser(
  clerkId: string,
  data: UserUpdate,
  getToken: GetTokenFn,
): Promise<UserDetail> {
  const res = await apiFetch(`/api/admin/users/${clerkId}`, getToken, {
    method: "PUT",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update user: ${res.status}`);
  return res.json();
}

// ---------- Usage ----------

export interface UsageAggregate {
  total_tokens: number;
  total_cost_microdollars: number;
  total_requests: number;
  period: string;
}

export interface UserUsageBreakdown {
  clerk_user_id: string;
  role: string;
  model_used: string;
  total_tokens: number;
  total_cost_microdollars: number;
  request_count: number;
}

export async function fetchGlobalUsage(
  getToken: GetTokenFn,
  period: "today" | "week" | "month" = "today",
): Promise<UsageAggregate> {
  const res = await apiFetch(`/api/admin/usage?period=${period}`, getToken);
  if (!res.ok) throw new Error(`Failed to fetch usage: ${res.status}`);
  return res.json();
}

export async function fetchUserUsage(
  clerkId: string,
  getToken: GetTokenFn,
  period: "today" | "week" | "month" = "today",
): Promise<UserUsageBreakdown[]> {
  const res = await apiFetch(
    `/api/admin/usage/${clerkId}?period=${period}`,
    getToken,
  );
  if (!res.ok) throw new Error(`Failed to fetch user usage: ${res.status}`);
  return res.json();
}
