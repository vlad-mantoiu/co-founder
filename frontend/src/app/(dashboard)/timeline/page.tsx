"use client";

import { useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function buildTimelineRedirectTarget(searchParams: Readonly<URLSearchParams>): string {
  const params = new URLSearchParams(searchParams.toString());
  const projectId = params.get("project") ?? params.get("projectId");

  params.delete("project");
  params.delete("projectId");

  if (!projectId) return "/projects";
  const query = params.toString();
  return query
    ? `/projects/${projectId}/timeline?${query}`
    : `/projects/${projectId}/timeline`;
}

export default function LegacyTimelineRedirectPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const target = useMemo(
    () => buildTimelineRedirectTarget(searchParams),
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
