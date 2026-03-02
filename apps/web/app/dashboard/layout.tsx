"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/useAuth";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import CommandPalette from "@/components/CommandPalette";
import ToastContainer from "@/components/ToastContainer";
import AlertBanner from "@/components/sentinel/AlertBanner";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading, email, role } = useAuth();
  const router = useRouter();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[rgb(var(--color-background))]">
        <Loader2 className="w-10 h-10 animate-spin text-accent" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen flex bg-[rgb(var(--color-background))]">
      <Sidebar
        userEmail={email}
        userRole={role}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <TopBar sidebarCollapsed={sidebarCollapsed} />
      <CommandPalette />
      <ToastContainer />
      <AlertBanner />
      <main
        className={`flex-1 transition-all duration-300 pt-14 ${
          sidebarCollapsed ? "ml-20" : "ml-72"
        }`}
      >
        <div className="px-6 py-6 max-w-[1440px]">{children}</div>
      </main>
    </div>
  );
}
