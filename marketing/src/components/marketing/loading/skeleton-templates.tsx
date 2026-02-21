"use client";

import { cn } from "@/lib/utils";

function SkeletonBlock({ className }: { className?: string }) {
  return (
    <div className={cn("relative overflow-hidden rounded-lg bg-white/[0.04]", className)}>
      <div className="absolute inset-0 -translate-x-full animate-shimmer-diagonal bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
    </div>
  );
}

/** For pages with hero sections: home, cofounder, how-it-works */
export function HeroSkeleton() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-32 pb-20">
      {/* Badge */}
      <SkeletonBlock className="h-7 w-40 rounded-full" />
      {/* Headline line 1 */}
      <SkeletonBlock className="h-12 w-[70%] mt-6" />
      {/* Headline line 2 */}
      <SkeletonBlock className="h-12 w-[50%] mt-3" />
      {/* Subtitle line 1 */}
      <SkeletonBlock className="h-5 w-[60%] mt-6" />
      {/* Subtitle line 2 */}
      <SkeletonBlock className="h-5 w-[45%] mt-2" />
      {/* CTA button */}
      <SkeletonBlock className="h-12 w-48 mt-8 rounded-xl" />
    </div>
  );
}

/** For pages with card grids: pricing, about */
export function ListSkeleton() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-32 pb-20">
      {/* Section heading */}
      <SkeletonBlock className="h-10 w-[40%] mx-auto" />
      {/* Subheading */}
      <SkeletonBlock className="h-5 w-[55%] mx-auto mt-4" />
      {/* Cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
        <SkeletonBlock className="h-72 rounded-2xl" />
        <SkeletonBlock className="h-72 rounded-2xl" />
        <SkeletonBlock className="h-72 rounded-2xl" />
      </div>
    </div>
  );
}

/** For long-form pages: privacy, terms, contact */
export function ContentSkeleton() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-32 pb-20">
      {/* Page heading */}
      <SkeletonBlock className="h-10 w-[50%]" />
      {/* Paragraph lines */}
      <SkeletonBlock className="h-4 w-full mt-6" />
      <SkeletonBlock className="h-4 w-[95%] mt-2" />
      <SkeletonBlock className="h-4 w-[88%] mt-2" />
      <SkeletonBlock className="h-4 w-[70%] mt-2" />
      {/* Section heading */}
      <SkeletonBlock className="h-7 w-[35%] mt-10" />
      {/* Second paragraph */}
      <SkeletonBlock className="h-4 w-full mt-4" />
      <SkeletonBlock className="h-4 w-[92%] mt-2" />
      <SkeletonBlock className="h-4 w-[80%] mt-2" />
    </div>
  );
}
