"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import {
  trackScrollDepth,
  trackSectionView,
  trackEngagement,
  trackOutboundClick,
  trackPricingView,
} from "@/lib/analytics";

const SCROLL_THRESHOLDS = [25, 50, 75, 90];
const ENGAGEMENT_THRESHOLDS = [30, 60, 120]; // seconds

/**
 * Drop this once inside the marketing layout. It passively tracks:
 * - Scroll depth (25/50/75/90%)
 * - Section visibility (any element with data-track-section)
 * - Engagement time milestones (30s, 60s, 120s)
 * - Outbound link clicks
 * - Pricing page view
 */
export function AnalyticsProvider() {
  const pathname = usePathname();
  const firedScrollRef = useRef(new Set<number>());
  const firedEngagementRef = useRef(new Set<number>());

  // Reset on route change
  useEffect(() => {
    firedScrollRef.current.clear();
    firedEngagementRef.current.clear();
  }, [pathname]);

  // Pricing page signal
  useEffect(() => {
    if (pathname === "/pricing" || pathname === "/pricing/") {
      trackPricingView();
    }
  }, [pathname]);

  // Scroll depth
  useEffect(() => {
    const onScroll = () => {
      const scrollPercent = Math.round(
        (window.scrollY / (document.body.scrollHeight - window.innerHeight)) *
          100,
      );
      for (const t of SCROLL_THRESHOLDS) {
        if (scrollPercent >= t && !firedScrollRef.current.has(t)) {
          firedScrollRef.current.add(t);
          trackScrollDepth(t);
        }
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [pathname]);

  // Section visibility (IntersectionObserver)
  useEffect(() => {
    const seen = new Set<string>();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const name = (entry.target as HTMLElement).dataset.trackSection;
          if (name && !seen.has(name)) {
            seen.add(name);
            trackSectionView(name);
          }
        }
      },
      { threshold: 0.3 },
    );

    const els = document.querySelectorAll("[data-track-section]");
    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [pathname]);

  // Engagement time
  useEffect(() => {
    let elapsed = 0;
    const id = setInterval(() => {
      elapsed += 1;
      for (const t of ENGAGEMENT_THRESHOLDS) {
        if (elapsed === t && !firedEngagementRef.current.has(t)) {
          firedEngagementRef.current.add(t);
          trackEngagement(t);
        }
      }
    }, 1000);
    return () => clearInterval(id);
  }, [pathname]);

  // Outbound link clicks
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      const anchor = (e.target as HTMLElement).closest("a");
      if (!anchor) return;
      const href = anchor.href;
      if (href && !href.startsWith(window.location.origin) && href.startsWith("http")) {
        trackOutboundClick(href);
      }
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  return null; // No UI — passive tracker
}
