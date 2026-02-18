"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/lib/auth-core";
import { useState } from "react";
import {
  Scale,
  LogOut,
  LayoutDashboard,
  Briefcase,
  Users,
  Clock,
  FileText,
  Receipt,
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
  ShieldAlert,
  ChevronLeft,
  ChevronRight,
  Moon,
  Sun,
  FolderOpen,
} from "lucide-react";

// NAV_ITEMS groupés par section
const NAV_GROUPS = [
  {
    label: "GESTION",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { label: "Dossiers", href: "/dashboard/cases", icon: Briefcase },
      { label: "Contacts", href: "/dashboard/contacts", icon: Users },
      { label: "Prestations", href: "/dashboard/billing", icon: Clock },
      { label: "Factures", href: "/dashboard/billing?tab=invoices", icon: Receipt },
      { label: "Documents", href: "/dashboard/documents", icon: FolderOpen },
    ],
  },
  {
    label: "COMMUNICATION",
    items: [
      { label: "Inbox", href: "/dashboard/inbox", icon: Inbox, badge: 3 },
      { label: "Emails", href: "/dashboard/emails", icon: Mail },
      { label: "Agenda", href: "/dashboard/calendar", icon: Calendar },
      { label: "Appels", href: "/dashboard/calls", icon: Phone },
    ],
  },
  {
    label: "INTELLIGENCE",
    items: [
      { label: "Recherche", href: "/dashboard/search", icon: Search },
      { label: "Graphe", href: "/dashboard/graph", icon: Share2 },
      { label: "Sentinel", href: "/dashboard/sentinel", icon: ShieldAlert },
      { label: "Hub IA", href: "/dashboard/ai", icon: Brain },
      { label: "Legal RAG", href: "/dashboard/legal", icon: Scale },
      { label: "Transcription", href: "/dashboard/ai/transcription", icon: Mic },
      { label: "Migration", href: "/dashboard/migration", icon: Upload },
    ],
  },
];

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
  const [darkMode, setDarkMode] = useState(false);

  // Initials
  const initials = userEmail
    ? userEmail.split("@")[0].split(".").map((p) => p[0]).slice(0, 2).join("").toUpperCase()
    : "U";

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-30 flex flex-col bg-primary transition-all duration-300 ${
        collapsed ? "w-20" : "w-72"
      }`}
    >
      {/* Logo */}
      <div
        className={`flex items-center gap-3 ${
          collapsed ? "justify-center px-4" : "px-6"
        } py-6 border-b border-white/10`}
      >
        <div className="w-10 h-10 rounded bg-primary/10 flex items-center justify-center">
          <Scale className="w-6 h-6 text-accent" />
        </div>
        {!collapsed && (
          <div>
            <h1 className="text-xl font-display font-bold text-white">LexiBel</h1>
            <p className="text-xs text-white/60">Legal Management</p>
          </div>
        )}
      </div>

      {/* Navigation Groups */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto space-y-6">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            {!collapsed && (
              <div className="px-3 mb-2 text-[10px] font-semibold text-white/40 tracking-wider">
                {group.label}
              </div>
            )}
            <div className="space-y-1">
              {group.items.map((item) => {
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/dashboard" && pathname.startsWith(item.href));

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={collapsed ? item.label : undefined}
                    className={`relative flex items-center gap-3 px-3 py-2.5 rounded transition-colors duration-150 group ${
                      isActive
                        ? "bg-white/10 text-white"
                        : "text-white/70 hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    {/* Active indicator */}
                    {isActive && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-accent rounded-r" />
                    )}

                    <item.icon
                      className={`w-5 h-5 flex-shrink-0 ${
                        collapsed ? "mx-auto" : ""
                      }`}
                    />

                    {!collapsed && (
                      <>
                        <span className="flex-1 text-sm font-medium">{item.label}</span>
                        {item.badge !== undefined && item.badge > 0 && (
                          <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-accent text-white rounded">
                            {item.badge}
                          </span>
                        )}
                      </>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}

        {/* Admin (conditionnel) */}
        {userRole === "super_admin" && (
          <div>
            {!collapsed && (
              <div className="px-3 mb-2 text-[10px] font-semibold text-white/40 tracking-wider">
                ADMINISTRATION
              </div>
            )}
            <Link
              href="/dashboard/admin"
              className={`relative flex items-center gap-3 px-3 py-2.5 rounded transition-colors duration-150 group ${
                pathname.startsWith("/dashboard/admin")
                  ? "bg-white/10 text-white"
                  : "text-white/70 hover:bg-white/10 hover:text-white"
              }`}
            >
              <Shield className="w-5 h-5 flex-shrink-0" />
              {!collapsed && <span className="text-sm font-medium">Admin</span>}
            </Link>
          </div>
        )}
      </nav>

      {/* User Section */}
      <div className="p-3 border-t border-white/10 space-y-2">
        {/* Dark Mode Toggle */}
        <button
          onClick={() => setDarkMode(!darkMode)}
          className="w-full flex items-center gap-3 px-3 py-2 rounded text-white/70 hover:bg-white/5 hover:text-white transition-colors duration-150"
        >
          {darkMode ? (
            <Sun className="w-4 h-4" />
          ) : (
            <Moon className="w-4 h-4" />
          )}
          {!collapsed && <span className="text-sm">Mode {darkMode ? "Clair" : "Sombre"}</span>}
        </button>

        {/* User Info */}
        <div className={`flex items-center gap-3 ${collapsed ? "justify-center" : "px-3"} py-2`}>
          <div className="w-9 h-9 rounded bg-primary/10 flex items-center justify-center text-sm font-semibold text-accent flex-shrink-0">
            {initials}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{userEmail}</p>
              <p className="text-[10px] text-white/50">{userRole}</p>
            </div>
          )}
        </div>

        {/* Logout */}
        <button
          onClick={() => logout()}
          className="w-full flex items-center gap-3 px-3 py-2 rounded text-white/70 hover:bg-white/5 hover:text-red-400 transition-colors duration-150"
        >
          <LogOut className="w-4 h-4" />
          {!collapsed && <span className="text-sm">Déconnexion</span>}
        </button>
      </div>

      {/* Collapse Toggle */}
      <button
        onClick={onToggle}
        className="absolute -right-3 top-6 w-6 h-6 bg-white rounded-full shadow-sm flex items-center justify-center text-primary hover:bg-accent hover:text-white transition-colors duration-150"
      >
        {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
      </button>
    </aside>
  );
}
