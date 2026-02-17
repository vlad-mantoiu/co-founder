"use client";

import { useParams, useSearchParams } from "next/navigation";
import { redirect } from "next/navigation";

/**
 * Legacy /company/[id]/deploy redirect.
 * Redirects to /projects/[id]/deploy (new canonical deploy route).
 */
export default function CompanyDeployRedirect() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const qs = searchParams.toString();
  redirect(`/projects/${params.id}/deploy${qs ? `?${qs}` : ""}`);
}
