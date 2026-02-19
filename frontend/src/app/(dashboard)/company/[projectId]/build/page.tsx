"use client";

import { useParams, useSearchParams } from "next/navigation";
import { redirect } from "next/navigation";

/**
 * Legacy /company/[id]/build redirect.
 * Redirects to /projects/[id]/build (new canonical build route).
 * Preserves ?job_id= query param for active build tracking.
 */
export default function CompanyBuildRedirect() {
  const params = useParams<{ projectId: string }>();
  const searchParams = useSearchParams();
  const qs = searchParams.toString();
  redirect(`/projects/${params.projectId}/build${qs ? `?${qs}` : ""}`);
}
