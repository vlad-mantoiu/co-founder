import { cn } from "@/lib/utils";

const variants = {
  default: "glass",
  strong: "glass-strong",
  glow: "glass shadow-glow",
} as const;

interface GlassCardProps {
  children: React.ReactNode;
  variant?: keyof typeof variants;
  className?: string;
}

export function GlassCard({
  children,
  variant = "default",
  className,
}: GlassCardProps) {
  return (
    <div className={cn(variants[variant], "rounded-2xl p-6", className)}>
      {children}
    </div>
  );
}
