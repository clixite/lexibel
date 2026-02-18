"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
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
  const { data: session, status } = useSession();
  const router = useRouter();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neutral-50">
        <Loader2 className="w-10 h-10 animate-spin text-accent" />
      </div>
    );
  }

  if (!session?.user) {
    return null;
  }

  const user = session.user as any;

  return (
    <div className="min-h-screen flex bg-neutral-50">
      <Sidebar
        userEmail={user.email || ""}
        userRole={user.role || ""}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <TopBar sidebarCollapsed={sidebarCollapsed} />
      <CommandPalette />
      <ToastContainer />
      <AlertBanner />
      <main
        className={`transition-all duration-300 pt-16 ${
          sidebarCollapsed ? "ml-20" : "ml-72"
        }`}
      >
        <div className="p-8">{children}</div>
      </main>
    </div>
  );
}
