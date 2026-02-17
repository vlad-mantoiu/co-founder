"use client";

import { useParams, useSearchParams } from "next/navigation";
import { redirect } from "next/navigation";

/**
 * Legacy /company/[projectId] redirect.
 * Redirects to /projects/[projectId] (new canonical dashboard route).
 */
export default function CompanyDashboardRedirect() {
  const params = useParams<{ projectId: string }>();
  const searchParams = useSearchParams();
  const qs = searchParams.toString();
  redirect(`/projects/${params.projectId}${qs ? `?${qs}` : ""}`);
}
