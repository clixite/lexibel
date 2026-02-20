"use client";

import { useState } from "react";
import { Calculator, Plus, Calendar as CalIcon } from "lucide-react";
import { Button, Badge } from "@/components/ui";

interface CalculatedDeadline {
  name: string;
  basis: string;
  date: string;
  daysRemaining: number;
}

const ACT_TYPES = [
  { value: "jugement_contradictoire", label: "Jugement contradictoire" },
  { value: "jugement_defaut", label: "Jugement par defaut" },
  { value: "arret_appel", label: "Arret (cour d'appel)" },
  { value: "arret_cassation", label: "Arret (cour de cassation)" },
  { value: "citation", label: "Citation" },
  { value: "signification", label: "Signification" },
];

const MATTERS = [
  { value: "civil", label: "Civil" },
  { value: "penal", label: "Penal" },
  { value: "commercial", label: "Commercial" },
  { value: "social", label: "Social" },
  { value: "fiscal", label: "Fiscal" },
  { value: "family", label: "Familial" },
];

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr);
  d.setDate(d.getDate() + days);
  return d.toISOString().split("T")[0];
}

function daysFromNow(dateStr: string): number {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const target = new Date(dateStr);
  return Math.ceil((target.getTime() - now.getTime()) / 86400000);
}

function computeDeadlines(actType: string, matter: string, actDate: string): CalculatedDeadline[] {
  const results: CalculatedDeadline[] = [];

  if (matter === "penal") {
    if (actType === "jugement_contradictoire" || actType === "jugement_defaut") {
      results.push({ name: "Appel", basis: "Art. 203 C.I.Cr. - 30 jours", date: addDays(actDate, 30), daysRemaining: 0 });
      results.push({ name: "Opposition", basis: "Art. 187 C.I.Cr. - 15 jours", date: addDays(actDate, 15), daysRemaining: 0 });
      results.push({ name: "Pourvoi en cassation", basis: "Art. 373 C.I.Cr. - 15 jours", date: addDays(actDate, 15), daysRemaining: 0 });
    }
    if (actType === "arret_appel") {
      results.push({ name: "Pourvoi en cassation", basis: "Art. 373 C.I.Cr. - 15 jours", date: addDays(actDate, 15), daysRemaining: 0 });
    }
  } else {
    // Civil, Commercial, Social, Fiscal, Family
    if (actType === "jugement_contradictoire") {
      results.push({ name: "Appel", basis: "Art. 1051 C. jud. - 30 jours", date: addDays(actDate, 30), daysRemaining: 0 });
      results.push({ name: "Opposition", basis: "Art. 1048 C. jud. - 30 jours", date: addDays(actDate, 30), daysRemaining: 0 });
      results.push({ name: "Pourvoi en cassation", basis: "Art. 1073 C. jud. - 3 mois", date: addDays(actDate, 90), daysRemaining: 0 });
    }
    if (actType === "jugement_defaut") {
      results.push({ name: "Opposition", basis: "Art. 1048 C. jud. - 30 jours", date: addDays(actDate, 30), daysRemaining: 0 });
      results.push({ name: "Appel", basis: "Art. 1051 C. jud. - 30 jours", date: addDays(actDate, 30), daysRemaining: 0 });
    }
    if (actType === "arret_appel") {
      results.push({ name: "Pourvoi en cassation", basis: "Art. 1073 C. jud. - 3 mois", date: addDays(actDate, 90), daysRemaining: 0 });
    }
    if (actType === "citation") {
      results.push({ name: "Delai de comparution", basis: "Art. 707 C. jud. - 8 jours", date: addDays(actDate, 8), daysRemaining: 0 });
    }
    if (actType === "signification") {
      results.push({ name: "Appel", basis: "Art. 1051 C. jud. - 30 jours", date: addDays(actDate, 30), daysRemaining: 0 });
    }

    // Social specifics
    if (matter === "social" && (actType === "jugement_contradictoire" || actType === "jugement_defaut")) {
      results.push({ name: "Appel (social)", basis: "Art. 1051 C. jud. - 30 jours", date: addDays(actDate, 30), daysRemaining: 0 });
    }

    // Fiscal reclamation
    if (matter === "fiscal" && actType === "signification") {
      results.push({ name: "Reclamation administrative", basis: "Art. 371 CIR - 6 mois", date: addDays(actDate, 180), daysRemaining: 0 });
    }
  }

  // Compute days remaining
  return results.map((r) => ({ ...r, daysRemaining: daysFromNow(r.date) }));
}

interface DeadlineCalculatorProps {
  onAddToCalendar?: (deadline: CalculatedDeadline) => void;
}

export default function DeadlineCalculator({ onAddToCalendar }: DeadlineCalculatorProps) {
  const [actType, setActType] = useState("");
  const [matter, setMatter] = useState("civil");
  const [actDate, setActDate] = useState("");
  const [results, setResults] = useState<CalculatedDeadline[]>([]);
  const [expanded, setExpanded] = useState(false);

  const calculate = () => {
    if (!actType || !actDate) return;
    const res = computeDeadlines(actType, matter, actDate);
    setResults(res);
  };

  return (
    <div className="bg-white rounded-lg border border-neutral-200">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-3 flex items-center justify-between hover:bg-neutral-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Calculator className="w-5 h-5 text-accent-600" />
          <span className="font-semibold text-neutral-900">Calculateur de delais belges</span>
        </div>
        <span className="text-sm text-neutral-400">{expanded ? "Fermer" : "Ouvrir"}</span>
      </button>

      {expanded && (
        <div className="px-5 pb-5 space-y-4 border-t border-neutral-100 pt-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Type d'acte</label>
              <select value={actType} onChange={(e) => setActType(e.target.value)} className="input text-sm">
                <option value="">-- Selectionnez --</option>
                {ACT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Matiere</label>
              <select value={matter} onChange={(e) => setMatter(e.target.value)} className="input text-sm">
                {MATTERS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Date de l'acte</label>
              <input type="date" value={actDate} onChange={(e) => setActDate(e.target.value)} className="input text-sm" />
            </div>
          </div>

          <Button variant="primary" size="sm" onClick={calculate} disabled={!actType || !actDate}>
            Calculer les delais
          </Button>

          {results.length > 0 && (
            <div className="overflow-hidden rounded-lg border border-neutral-200">
              <table className="w-full text-sm">
                <thead className="bg-neutral-50">
                  <tr>
                    <th className="text-left px-4 py-2 text-xs font-semibold text-neutral-600 uppercase">Delai</th>
                    <th className="text-left px-4 py-2 text-xs font-semibold text-neutral-600 uppercase">Base legale</th>
                    <th className="text-left px-4 py-2 text-xs font-semibold text-neutral-600 uppercase">Date limite</th>
                    <th className="text-center px-4 py-2 text-xs font-semibold text-neutral-600 uppercase">Jours</th>
                    <th className="text-center px-4 py-2 text-xs font-semibold text-neutral-600 uppercase"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100">
                  {results.map((r, i) => (
                    <tr key={i} className="hover:bg-neutral-50">
                      <td className="px-4 py-2 font-medium text-neutral-800">{r.name}</td>
                      <td className="px-4 py-2 text-neutral-500 text-xs">{r.basis}</td>
                      <td className="px-4 py-2 text-neutral-700">{new Date(r.date).toLocaleDateString("fr-BE")}</td>
                      <td className="px-4 py-2 text-center">
                        <Badge
                          variant={r.daysRemaining <= 3 ? "danger" : r.daysRemaining <= 7 ? "warning" : r.daysRemaining <= 14 ? "warning" : "default"}
                          size="sm"
                        >
                          {r.daysRemaining}j
                        </Badge>
                      </td>
                      <td className="px-4 py-2 text-center">
                        {onAddToCalendar && (
                          <button
                            type="button"
                            onClick={() => onAddToCalendar(r)}
                            className="text-accent-600 hover:text-accent-700"
                            title="Ajouter au calendrier"
                          >
                            <Plus className="w-4 h-4" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
