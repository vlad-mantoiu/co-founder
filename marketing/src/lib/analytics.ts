/* ─────────────────────────────────────────────
   GA4 event helpers — thin wrappers around gtag()
   ───────────────────────────────────────────── */

type GtagEvent = [string, string, Record<string, unknown>?];

function push(...args: GtagEvent) {
  if (typeof window !== "undefined" && typeof window.gtag === "function") {
    window.gtag(...args);
  }
}

/* ── Conversion ── */

/** Waitlist form submitted successfully. Mark as key event in GA4. */
export function trackWaitlistSignup(email: string) {
  push("event", "waitlist_signup", {
    method: "form",
    email_domain: email.split("@")[1] ?? "unknown",
  });
}

/* ── CTA / Navigation ── */

/** Any call-to-action button clicked. */
export function trackCtaClick(label: string, location: string) {
  push("event", "cta_click", { cta_label: label, cta_location: location });
}

/** Outbound link clicked. */
export function trackOutboundClick(url: string) {
  push("event", "outbound_click", { link_url: url });
}

/* ── Engagement ── */

/** User scrolled past a percentage threshold. */
export function trackScrollDepth(percent: number) {
  push("event", "scroll_depth", { percent_scrolled: percent });
}

/** A named section became visible in the viewport. */
export function trackSectionView(section: string) {
  push("event", "section_view", { section_name: section });
}

/** User stayed on page longer than threshold (seconds). */
export function trackEngagement(seconds: number) {
  push("event", "engagement_milestone", { seconds_on_page: seconds });
}

/** Pricing page viewed (higher intent signal). */
export function trackPricingView() {
  push("event", "pricing_view");
}

/* ── Types ── */

declare global {
  interface Window {
    gtag: (...args: unknown[]) => void;
    dataLayer: unknown[];
  }
}
