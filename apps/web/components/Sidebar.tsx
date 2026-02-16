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
  Upload,
  Share2,
} from "lucide-react";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: Home },
  { label: "Dossiers", href: "/dashboard/cases", icon: Briefcase },
  { label: "Contacts", href: "/dashboard/contacts", icon: Users },
  { label: "Timeline", href: "/dashboard/timeline", icon: Clock },
  { label: "Facturation", href: "/dashboard/billing", icon: FileText },
  { label: "Inbox", href: "/dashboard/inbox", icon: Inbox },
  { label: "Migration", href: "/dashboard/migration", icon: Upload },
  { label: "Graphe", href: "/dashboard/graph", icon: Share2 },
];

interface SidebarProps {
  userEmail: string;
  userRole: string;
}

export default function Sidebar({ userEmail, userRole }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-slate-800 text-white flex flex-col fixed inset-y-0 left-0">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-700">
        <Scale className="w-7 h-7 text-blue-400" />
        <span className="text-xl font-bold tracking-tight">LexiBel</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 ${
                isActive
                  ? "bg-slate-700 text-white"
                  : "text-slate-300 hover:bg-slate-700 hover:text-white"
              }`}
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* User section + Logout */}
      <div className="px-4 py-4 border-t border-slate-700">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-sm font-semibold">
            {userEmail?.[0]?.toUpperCase() || "U"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{userEmail}</p>
            <p className="text-xs text-slate-400 truncate">{userRole}</p>
          </div>
        </div>
        <button
          onClick={() => signOut({ callbackUrl: "/login" })}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm font-medium
                     text-slate-300 hover:bg-slate-700 hover:text-white transition-colors duration-150"
        >
          <LogOut className="w-4 h-4" />
          Se déconnecter
        </button>
      </div>
    </aside>
  );
}
