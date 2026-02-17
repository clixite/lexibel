"use client";

import { useState } from "react";
import { Search, Bell, ChevronRight } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface TopBarProps {
  sidebarCollapsed: boolean;
}

export default function TopBar({ sidebarCollapsed }: TopBarProps) {
  const pathname = usePathname();
  const [searchOpen, setSearchOpen] = useState(false);

  // Breadcrumb from pathname
  const pathSegments = pathname.split("/").filter(Boolean);
  const breadcrumbs = pathSegments.map((segment, index) => ({
    label: segment.charAt(0).toUpperCase() + segment.slice(1),
    href: "/" + pathSegments.slice(0, index + 1).join("/"),
  }));

  return (
    <header
      className={`fixed top-0 right-0 z-20 h-16 bg-white border-b border-neutral-200 transition-all duration-300 ${
        sidebarCollapsed ? "left-20" : "left-72"
      }`}
    >
      <div className="h-full px-6 flex items-center justify-between">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm">
          {breadcrumbs.map((crumb, index) => (
            <div key={crumb.href} className="flex items-center gap-2">
              {index > 0 && <ChevronRight className="w-4 h-4 text-neutral-400" />}
              <Link
                href={crumb.href}
                className={`${
                  index === breadcrumbs.length - 1
                    ? "font-semibold text-primary"
                    : "text-neutral-600 hover:text-primary"
                }`}
              >
                {crumb.label}
              </Link>
            </div>
          ))}
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-3">
          {/* Search */}
          <button
            onClick={() => setSearchOpen(!searchOpen)}
            className="p-2 rounded-lg hover:bg-neutral-100 transition-colors"
            title="Recherche (Cmd+K)"
          >
            <Search className="w-5 h-5 text-neutral-600" />
          </button>

          {/* Notifications */}
          <button className="relative p-2 rounded-lg hover:bg-neutral-100 transition-colors">
            <Bell className="w-5 h-5 text-neutral-600" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
          </button>
        </div>
      </div>

      {/* Search Modal Placeholder */}
      {searchOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-start justify-center pt-20"
          onClick={() => setSearchOpen(false)}
        >
          <div
            className="bg-white rounded-xl shadow-2xl w-full max-w-2xl p-4 animate-scaleIn"
            onClick={(e) => e.stopPropagation()}
          >
            <input
              type="text"
              placeholder="Rechercher des dossiers, contacts, documents..."
              className="w-full px-4 py-3 text-lg border-none outline-none"
              autoFocus
            />
            <div className="mt-4 text-sm text-neutral-500 text-center">
              Tapez pour rechercher...
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
