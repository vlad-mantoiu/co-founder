"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { fetchUsers, type UserSummary } from "@/lib/admin-api";
import { UserTable } from "@/components/admin/UserTable";
import { Search } from "lucide-react";

export default function AdminUsersPage() {
  const { getToken } = useAuth();
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchUsers(getToken, {
        page,
        per_page: 50,
        search: search || undefined,
      });
      setUsers(data);
    } catch {
      // Non-fatal
    } finally {
      setLoading(false);
    }
  }, [getToken, page, search]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-display font-semibold text-white">
          Users
        </h1>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by user ID..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-9 pr-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder:text-muted-foreground w-64"
          />
        </div>
      </div>

      {loading ? (
        <div className="text-muted-foreground text-sm animate-pulse">
          Loading users...
        </div>
      ) : (
        <>
          <UserTable users={users} />
          <div className="flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded-lg bg-white/5 text-sm text-muted-foreground hover:text-white disabled:opacity-30"
            >
              Previous
            </button>
            <span className="text-xs text-muted-foreground">Page {page}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={users.length < 50}
              className="px-3 py-1.5 rounded-lg bg-white/5 text-sm text-muted-foreground hover:text-white disabled:opacity-30"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
