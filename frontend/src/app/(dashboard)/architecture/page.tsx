"use client";

import { useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function buildArchitectureRedirectTarget(
  searchParams: Readonly<URLSearchParams>,
): string {
  const params = new URLSearchParams(searchParams.toString());
  const projectId = params.get("project") ?? params.get("projectId");

  params.delete("project");
  params.delete("projectId");

  if (!projectId) return "/projects";
  const query = params.toString();
  return query
    ? `/projects/${projectId}/architecture?${query}`
    : `/projects/${projectId}/architecture`;
}

export default function LegacyArchitectureRedirectPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const target = useMemo(
    () => buildArchitectureRedirectTarget(searchParams),
    [searchParams],
  );

  useEffect(() => {
    router.replace(target);
  }, [router, target]);

  return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
    </div>
  );
}
