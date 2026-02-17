"use client";

import { useSearchParams } from "next/navigation";
import { redirect } from "next/navigation";

/**
 * Legacy Understanding route redirect.
 *
 * Redirects to the new project-scoped understanding URL:
 * /understanding?projectId={id}&sessionId={session} → /projects/{id}/understanding?sessionId={session}
 */
export default function UnderstandingRedirect() {
  const searchParams = useSearchParams();
  const projectId = searchParams.get("projectId");
  if (projectId) {
    // Preserve all other query params (sessionId etc.) in the redirect
    redirect(`/projects/${projectId}/understanding?${searchParams.toString()}`);
  }
  redirect("/dashboard");
}
