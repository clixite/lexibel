"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/lib/auth-core";
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
  Settings,
  Shield,
  ShieldAlert,
  ChevronLeft,
  ChevronRight,
  FolderOpen,
  BarChart3,
} from "lucide-react";

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
      { label: "Analytique", href: "/dashboard/analytics", icon: BarChart3 },
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
      { label: "Sentinel", href: "/dashboard/sentinel", icon: ShieldAlert },
      { label: "Intelligence IA", href: "/dashboard/brain", icon: Brain },
      { label: "Legal RAG", href: "/dashboard/legal", icon: Scale },
      { label: "Graphe", href: "/dashboard/graph", icon: Share2 },
    ],
  },
  {
    label: "OUTILS",
    items: [
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

  const initials = userEmail
    ? userEmail
        .split("@")[0]
        .split(".")
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "U";

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-30 flex flex-col transition-all duration-300 border-r ${
        collapsed ? "w-20" : "w-72"
      }`}
      style={{
        background: "rgb(var(--sidebar-bg))",
        borderColor: "rgb(var(--sidebar-border))",
      }}
    >
      {/* Logo */}
      <div
        className={`flex items-center gap-3 ${
          collapsed ? "justify-center px-4" : "px-6"
        } py-5 border-b`}
        style={{ borderColor: "rgb(var(--sidebar-border))" }}
      >
        <div
          className="w-10 h-10 rounded-sm flex items-center justify-center flex-shrink-0"
          style={{
            background: "rgba(212,175,55,0.1)",
            border: "1px solid rgba(212,175,55,0.2)",
          }}
        >
          <Scale className="w-5 h-5 text-accent" />
        </div>
        {!collapsed && (
          <div>
            <h1
              className="text-lg font-bold text-white leading-none"
              style={{ fontFamily: "var(--font-display)" }}
            >
              LexiBel
            </h1>
            <p className="text-[11px] mt-0.5" style={{ color: "rgb(var(--sidebar-text-muted))" }}>
              Legal Management
            </p>
          </div>
        )}
      </div>

      {/* Navigation Groups */}
      <nav className="flex-1 px-2 py-4 overflow-y-auto space-y-5">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            {!collapsed && (
              <div
                className="px-3 mb-1.5 text-[10px] font-bold uppercase tracking-[0.08em]"
                style={{ color: "rgb(var(--sidebar-text-muted))" }}
              >
                {group.label}
              </div>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/dashboard" &&
                    (pathname.startsWith(item.href + "/") ||
                      pathname === item.href));

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={collapsed ? item.label : undefined}
                    className={`relative flex items-center gap-3 px-3 py-2 rounded-sm transition-colors duration-150 group ${
                      isActive
                        ? "text-white"
                        : "hover:text-white"
                    }`}
                    style={
                      isActive
                        ? { background: "rgba(212,175,55,0.10)" }
                        : { color: "rgb(var(--sidebar-text))" }
                    }
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        (e.currentTarget as HTMLElement).style.background =
                          "rgba(255,255,255,0.05)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        (e.currentTarget as HTMLElement).style.background = "";
                      }
                    }}
                  >
                    {/* Active indicator — 3px gold strip */}
                    {isActive && (
                      <span
                        className="absolute left-0 inset-y-1 w-[3px] bg-accent rounded-r"
                      />
                    )}

                    <item.icon
                      className={`w-4 h-4 flex-shrink-0 ${
                        collapsed ? "mx-auto" : ""
                      } ${isActive ? "text-accent" : ""}`}
                    />

                    {!collapsed && (
                      <>
                        <span className="flex-1 text-sm font-medium">
                          {item.label}
                        </span>
                        {"badge" in item &&
                          item.badge !== undefined &&
                          item.badge > 0 && (
                            <span
                              className="px-1.5 py-0.5 text-[10px] font-bold rounded-[2px] bg-accent text-[#0F172A]"
                            >
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
              <div
                className="px-3 mb-1.5 text-[10px] font-bold uppercase tracking-[0.08em]"
                style={{ color: "rgb(var(--sidebar-text-muted))" }}
              >
                ADMINISTRATION
              </div>
            )}
            <div className="space-y-0.5">
              {[
                { href: "/dashboard/admin", icon: Shield, label: "Admin" },
                {
                  href: "/dashboard/admin/settings",
                  icon: Settings,
                  label: "Paramètres",
                },
              ].map(({ href, icon: Icon, label }) => (
                <Link
                  key={href}
                  href={href}
                  title={collapsed ? label : undefined}
                  className={`relative flex items-center gap-3 px-3 py-2 rounded-sm transition-colors duration-150 ${
                    pathname === href ? "text-white" : "hover:text-white"
                  }`}
                  style={
                    pathname === href
                      ? { background: "rgba(212,175,55,0.10)" }
                      : { color: "rgb(var(--sidebar-text))" }
                  }
                  onMouseEnter={(e) => {
                    if (pathname !== href)
                      (e.currentTarget as HTMLElement).style.background =
                        "rgba(255,255,255,0.05)";
                  }}
                  onMouseLeave={(e) => {
                    if (pathname !== href)
                      (e.currentTarget as HTMLElement).style.background = "";
                  }}
                >
                  {pathname === href && (
                    <span className="absolute left-0 inset-y-1 w-[3px] bg-accent rounded-r" />
                  )}
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {!collapsed && (
                    <span className="text-sm font-medium">{label}</span>
                  )}
                </Link>
              ))}
            </div>
          </div>
        )}
      </nav>

      {/* User Section */}
      <div
        className="p-3 border-t space-y-1"
        style={{ borderColor: "rgb(var(--sidebar-border))" }}
      >
        {/* User Info */}
        <div
          className={`flex items-center gap-3 ${collapsed ? "justify-center" : "px-2"} py-2`}
        >
          <div
            className="w-8 h-8 rounded-sm flex items-center justify-center text-xs font-bold flex-shrink-0"
            style={{
              background: "rgba(212,175,55,0.15)",
              border: "1px solid rgba(212,175,55,0.25)",
              color: "#D4AF37",
            }}
          >
            {initials}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate leading-none">
                {userEmail}
              </p>
              <p
                className="text-[10px] mt-0.5 uppercase tracking-wide"
                style={{ color: "rgb(var(--sidebar-text-muted))" }}
              >
                {userRole}
              </p>
            </div>
          )}
        </div>

        {/* Logout */}
        <button
          onClick={() => logout()}
          className="w-full flex items-center gap-3 px-2 py-2 rounded-sm transition-colors duration-150 hover:text-red-400"
          style={{ color: "rgb(var(--sidebar-text-muted))" }}
          onMouseEnter={(e) =>
            ((e.currentTarget as HTMLElement).style.background =
              "rgba(255,255,255,0.04)")
          }
          onMouseLeave={(e) =>
            ((e.currentTarget as HTMLElement).style.background = "")
          }
        >
          <LogOut className="w-4 h-4 flex-shrink-0" />
          {!collapsed && <span className="text-sm">Déconnexion</span>}
        </button>
      </div>

      {/* Collapse Toggle */}
      <button
        onClick={onToggle}
        className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-10 flex items-center justify-center rounded-r-md transition-colors duration-150"
        style={{
          background: "rgb(var(--sidebar-active-bg))",
          border: "1px solid rgb(var(--sidebar-border))",
          color: "rgb(var(--sidebar-text-muted))",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLElement).style.color = "#D4AF37";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLElement).style.color =
            "rgb(var(--sidebar-text-muted))";
        }}
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
