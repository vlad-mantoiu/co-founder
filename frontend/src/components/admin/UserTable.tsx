"use client";

import Link from "next/link";
import type { UserSummary } from "@/lib/admin-api";

interface Props {
  users: UserSummary[];
}

export function UserTable({ users }: Props) {
  return (
    <div className="overflow-x-auto rounded-xl border border-white/5">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/5 bg-white/[0.02]">
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
              User ID
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Plan
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Status
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Daily Tokens
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Joined
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {users.map((u) => (
            <tr
              key={u.clerk_user_id}
              className="hover:bg-white/[0.02] transition-colors"
            >
              <td className="px-4 py-3">
                <Link
                  href={`/admin/users/${u.clerk_user_id}`}
                  className="text-brand hover:underline font-mono text-xs"
                >
                  {u.clerk_user_id}
                </Link>
              </td>
              <td className="px-4 py-3">
                <span className="inline-block rounded-full bg-white/5 px-2.5 py-0.5 text-xs font-medium text-white">
                  {u.plan_slug}
                </span>
              </td>
              <td className="px-4 py-3">
                {u.is_suspended ? (
                  <span className="text-red-400 text-xs font-medium">Suspended</span>
                ) : u.is_admin ? (
                  <span className="text-brand text-xs font-medium">Admin</span>
                ) : (
                  <span className="text-green-400 text-xs font-medium">Active</span>
                )}
              </td>
              <td className="px-4 py-3 text-right font-mono text-xs text-muted-foreground">
                {u.daily_tokens_used.toLocaleString()}
              </td>
              <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                {new Date(u.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
          {users.length === 0 && (
            <tr>
              <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                No users found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
