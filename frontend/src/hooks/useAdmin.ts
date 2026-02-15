"use client";

import { useUser } from "@clerk/nextjs";

export function useAdmin(): { isAdmin: boolean; isLoaded: boolean } {
  const { user, isLoaded } = useUser();

  if (!isLoaded || !user) {
    return { isAdmin: false, isLoaded };
  }

  const admin = (user.publicMetadata as Record<string, unknown>)?.admin;
  return { isAdmin: admin === true, isLoaded };
}
