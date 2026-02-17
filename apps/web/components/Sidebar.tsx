"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import {
  Scale,
  LogOut,
  Home,
  Briefcase,
  Users,
  Clock,
  FileText,
  Inbox,
  Mail,
  Calendar,
  Phone,
  Search,
  Share2,
  Brain,
  Mic,
  Upload,
  Shield,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: Home },
  { label: "Dossiers", href: "/dashboard/cases", icon: Briefcase },
  { label: "Contacts", href: "/dashboard/contacts", icon: Users },
  { label: "Timeline", href: "/dashboard/timeline", icon: Clock },
  { label: "Facturation", href: "/dashboard/billing", icon: FileText },
  { label: "Inbox", href: "/dashboard/inbox", icon: Inbox },
  { label: "Emails", href: "/dashboard/emails", icon: Mail },
  { label: "Agenda", href: "/dashboard/calendar", icon: Calendar },
  { label: "Appels", href: "/dashboard/calls", icon: Phone },
  { label: "Recherche", href: "/dashboard/search", icon: Search },
  { label: "Graphe", href: "/dashboard/graph", icon: Share2 },
  { label: "Hub IA", href: "/dashboard/ai", icon: Brain },
  { label: "Legal RAG", href: "/dashboard/legal", icon: Scale },
  { label: "Transcription", href: "/dashboard/ai/transcription", icon: Mic },
  { label: "Migration", href: "/dashboard/migration", icon: Upload },
];

const ADMIN_ITEM = {
  label: "Admin",
  href: "/dashboard/admin",
  icon: Shield,
};

interface SidebarProps {
  userEmail: string;
  userRole: string;
  collapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({
  userEmail,
  userRole,
  collapsed,
  onToggle,
}: SidebarProps) {
  const pathname = usePathname();

  const navItems =
    userRole === "super_admin" ? [...NAV_ITEMS, ADMIN_ITEM] : NAV_ITEMS;

  const initials = userEmail
    ? userEmail
        .split("@")[0]
        .split(".")
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "U";

  const roleBadgeColor =
    userRole === "super_admin"
      ? "bg-accent-500/20 text-accent-300"
      : userRole === "admin"
        ? "bg-warning-500/20 text-warning-300"
        : "bg-white/10 text-neutral-400";

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-30 flex flex-col transition-all duration-300 ease-in-out ${
        collapsed ? "w-16" : "w-64"
      }`}
      style={{
        background: "linear-gradient(180deg, #0A2540 0%, #0D2E4D 100%)",
      }}
    >
      {/* Logo */}
      <div
        className={`flex items-center ${collapsed ? "justify-center px-2" : "px-6"} py-5 border-b border-white/10`}
      >
        <Scale className="w-7 h-7 text-accent flex-shrink-0" />
        {!collapsed && (
          <span className="ml-3 text-xl font-bold text-white tracking-tight">
            LexiBel
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={`relative flex items-center ${collapsed ? "justify-center" : ""} gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                isActive
                  ? "bg-white/15 text-white"
                  : "text-neutral-400 hover:bg-white/10 hover:text-white"
              }`}
            >
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-accent rounded-r-full" />
              )}
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {!collapsed && item.label}
            </Link>
          );
        })}
      </nav>

      {/* User section */}
      <div
        className={`px-3 py-4 border-t border-white/10 ${collapsed ? "flex flex-col items-center" : ""}`}
      >
        {!collapsed ? (
          <>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 rounded-full bg-accent/20 flex items-center justify-center text-sm font-semibold text-accent-300 flex-shrink-0">
                {initials}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">
                  {userEmail}
                </p>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium mt-0.5 ${roleBadgeColor}`}
                >
                  {userRole}
                </span>
              </div>
            </div>
            <button
              onClick={() => signOut({ callbackUrl: "/login" })}
              className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm font-medium
                         text-neutral-400 hover:bg-white/10 hover:text-white transition-all duration-150"
            >
              <LogOut className="w-4 h-4" />
              Se déconnecter
            </button>
          </>
        ) : (
          <>
            <div className="w-9 h-9 rounded-full bg-accent/20 flex items-center justify-center text-sm font-semibold text-accent-300 mb-2">
              {initials}
            </div>
            <button
              onClick={() => signOut({ callbackUrl: "/login" })}
              title="Se déconnecter"
              className="p-2 rounded-lg text-neutral-400 hover:bg-white/10 hover:text-white transition-all duration-150"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </>
        )}
      </div>

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        className="absolute top-5 -right-3 w-6 h-6 bg-white rounded-full shadow-medium flex items-center justify-center text-neutral-500 hover:text-neutral-900 transition-colors duration-150"
      >
        {collapsed ? (
          <ChevronRight className="w-3.5 h-3.5" />
        ) : (
          <ChevronLeft className="w-3.5 h-3.5" />
        )}
      </button>
    </aside>
  );
}
