"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, FileText, Users, Briefcase, Plus, Settings, Home, BarChart3, Calendar, Phone } from "lucide-react";

interface Command {
  id: string;
  label: string;
  icon: React.ReactNode;
  keywords: string[];
  action: () => void;
  shortcut?: string;
  category?: string;
}

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const router = useRouter();

  // Cmd+K or Ctrl+K to open
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const commands: Command[] = [
    // Navigation
    {
      id: "nav-dashboard",
      label: "Dashboard",
      icon: <Home className="w-4 h-4" />,
      keywords: ["home", "overview", "accueil"],
      action: () => router.push("/dashboard"),
      category: "Navigation"
    },
    {
      id: "nav-cases",
      label: "Dossiers",
      icon: <Briefcase className="w-4 h-4" />,
      keywords: ["cases", "files", "affaires"],
      action: () => router.push("/dashboard/cases"),
      category: "Navigation"
    },
    {
      id: "nav-contacts",
      label: "Contacts",
      icon: <Users className="w-4 h-4" />,
      keywords: ["people", "clients", "personnes"],
      action: () => router.push("/dashboard/contacts"),
      category: "Navigation"
    },
    {
      id: "nav-calendar",
      label: "Calendrier",
      icon: <Calendar className="w-4 h-4" />,
      keywords: ["calendar", "agenda", "events"],
      action: () => router.push("/dashboard/calendar"),
      category: "Navigation"
    },
    {
      id: "nav-calls",
      label: "Appels",
      icon: <Phone className="w-4 h-4" />,
      keywords: ["calls", "phone", "téléphone"],
      action: () => router.push("/dashboard/calls"),
      category: "Navigation"
    },
    {
      id: "nav-analytics",
      label: "Analyses",
      icon: <BarChart3 className="w-4 h-4" />,
      keywords: ["analytics", "stats", "statistiques"],
      action: () => router.push("/dashboard/analytics"),
      category: "Navigation"
    },

    // Actions
    {
      id: "new-case",
      label: "Nouveau dossier",
      icon: <Plus className="w-4 h-4" />,
      keywords: ["create", "add", "new", "créer", "nouveau"],
      action: () => router.push("/dashboard/cases"),
      shortcut: "N",
      category: "Actions"
    },
    {
      id: "new-contact",
      label: "Nouveau contact",
      icon: <Plus className="w-4 h-4" />,
      keywords: ["create", "add", "créer"],
      action: () => router.push("/dashboard/contacts"),
      shortcut: "C",
      category: "Actions"
    },

    // Search
    {
      id: "search-global",
      label: "Recherche globale",
      icon: <Search className="w-4 h-4" />,
      keywords: ["find", "search", "chercher", "trouver"],
      action: () => router.push("/dashboard/search"),
      shortcut: "/",
      category: "Recherche"
    },

    // Settings
    {
      id: "settings",
      label: "Paramètres",
      icon: <Settings className="w-4 h-4" />,
      keywords: ["settings", "preferences", "config"],
      action: () => router.push("/dashboard/settings"),
      category: "Système"
    },
  ];

  const filtered = commands.filter((cmd) =>
    cmd.label.toLowerCase().includes(query.toLowerCase()) ||
    cmd.keywords.some((k) => k.includes(query.toLowerCase()))
  );

  // Keyboard navigation
  useEffect(() => {
    if (!open) return;

    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => (i + 1) % filtered.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => (i - 1 + filtered.length) % filtered.length);
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filtered[selectedIndex]) {
          filtered[selectedIndex].action();
          setOpen(false);
          setQuery("");
          setSelectedIndex(0);
        }
      }
    };

    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, filtered, selectedIndex]);

  // Reset selected index when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  if (!open) return null;

  // Group commands by category
  const groupedCommands = filtered.reduce((acc, cmd) => {
    const category = cmd.category || "Autre";
    if (!acc[category]) acc[category] = [];
    acc[category].push(cmd);
    return acc;
  }, {} as Record<string, Command[]>);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={() => {
        setOpen(false);
        setQuery("");
        setSelectedIndex(0);
      }}
    >
      <div className="fixed top-20 left-1/2 -translate-x-1/2 w-full max-w-xl">
        <div
          className="bg-white rounded shadow-lg border border-neutral-200 animate-in slide-in-from-top-4 duration-150"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Search Input */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-neutral-200">
            <Search className="w-5 h-5 text-neutral-400" />
            <input
              type="text"
              placeholder="Rechercher ou taper une commande..."
              className="flex-1 outline-none text-sm"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
            />
            <kbd className="px-2 py-1 text-xs bg-neutral-100 text-neutral-600 rounded font-mono">
              {navigator.platform.indexOf("Mac") === 0 ? "⌘K" : "Ctrl+K"}
            </kbd>
          </div>

          {/* Commands List */}
          <div className="max-h-96 overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-neutral-500">
                Aucun résultat trouvé
              </div>
            ) : (
              <div>
                {Object.entries(groupedCommands).map(([category, cmds]) => (
                  <div key={category}>
                    <div className="px-4 py-2 text-xs font-semibold text-neutral-500 uppercase tracking-wider bg-neutral-50">
                      {category}
                    </div>
                    {cmds.map((cmd, index) => {
                      const globalIndex = filtered.indexOf(cmd);
                      const isSelected = globalIndex === selectedIndex;

                      return (
                        <button
                          key={cmd.id}
                          onClick={() => {
                            cmd.action();
                            setOpen(false);
                            setQuery("");
                            setSelectedIndex(0);
                          }}
                          className={`w-full flex items-center gap-3 px-4 py-2.5 transition-colors duration-150 text-left ${
                            isSelected ? "bg-primary/10 text-primary" : "hover:bg-neutral-50"
                          }`}
                        >
                          <span className={isSelected ? "text-primary" : "text-neutral-400"}>
                            {cmd.icon}
                          </span>
                          <span className="flex-1 text-sm text-neutral-900">{cmd.label}</span>
                          {cmd.shortcut && (
                            <kbd className="px-2 py-0.5 text-xs bg-neutral-100 text-neutral-600 rounded font-mono">
                              {cmd.shortcut}
                            </kbd>
                          )}
                        </button>
                      );
                    })}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-4 py-2 border-t border-neutral-200 text-xs text-neutral-500">
            <span>↑↓ naviguer</span>
            <span>⏎ sélectionner</span>
            <span>Esc fermer</span>
          </div>
        </div>
      </div>
    </div>
  );
}
