"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { BrandNav } from "@/components/ui/brand-nav";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { useAdmin } from "@/hooks/useAdmin";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAdmin, isLoaded } = useAdmin();
  const router = useRouter();

  useEffect(() => {
    if (isLoaded && !isAdmin) {
      router.replace("/dashboard");
    }
  }, [isAdmin, isLoaded, router]);

  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-obsidian bg-grid flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (!isAdmin) {
    return null;
  }

  return (
    <div className="min-h-screen bg-obsidian bg-grid">
      <BrandNav />
      <div className="pt-16 flex min-h-[calc(100vh-4rem)]">
        <AdminSidebar />
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
