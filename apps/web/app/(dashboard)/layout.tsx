import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import { Scale, LogOut, Home, Briefcase, Clock, FileText, Users, Settings } from "lucide-react";

const NAV_ITEMS = [
  { label: "Tableau de bord", href: "/dashboard", icon: Home },
  { label: "Dossiers", href: "/dashboard/cases", icon: Briefcase },
  { label: "Temps", href: "/dashboard/time", icon: Clock },
  { label: "Facturation", href: "/dashboard/invoices", icon: FileText },
  { label: "Contacts", href: "/dashboard/contacts", icon: Users },
  { label: "Paramètres", href: "/dashboard/settings", icon: Settings },
];

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();

  if (!session?.user) {
    redirect("/login");
  }

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-primary text-white flex flex-col fixed inset-y-0 left-0">
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-primary-400">
          <Scale className="w-7 h-7" />
          <span className="text-xl font-bold tracking-tight">LexiBel</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                         text-primary-100 hover:bg-primary-400 hover:text-white
                         transition-colors duration-150"
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </a>
          ))}
        </nav>

        {/* User section */}
        <div className="px-4 py-4 border-t border-primary-400">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-sm font-semibold">
              {session.user.email?.[0]?.toUpperCase() || "U"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {session.user.name || session.user.email}
              </p>
              <p className="text-xs text-primary-200 truncate">
                {session.user.role}
              </p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 ml-64">
        <div className="p-8">{children}</div>
      </main>
    </div>
  );
}
