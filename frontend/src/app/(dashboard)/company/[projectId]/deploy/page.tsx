"use client";

import { useParams, useSearchParams } from "next/navigation";
import { redirect } from "next/navigation";

/**
 * Legacy /company/[id]/deploy redirect.
 * Redirects to /projects/[id]/deploy (new canonical deploy route).
 */
export default function CompanyDeployRedirect() {
  const params = useParams<{ projectId: string }>();
  const searchParams = useSearchParams();
  const qs = searchParams.toString();
  redirect(`/projects/${params.projectId}/deploy${qs ? `?${qs}` : ""}`);
}
