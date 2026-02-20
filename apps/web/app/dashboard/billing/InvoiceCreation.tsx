"use client";

import { useEffect, useState, useCallback } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Check,
  Plus,
  Trash2,
  Search,
  Loader2,
  FileText,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface CaseOption {
  id: string;
  reference: string;
  title: string;
}

interface ContactOption {
  id: string;
  first_name: string;
  last_name: string;
  company_name: string | null;
  email: string;
}

interface TimeEntry {
  id: string;
  date: string;
  description: string;
  duration_minutes: number;
  hourly_rate_cents: number | null;
  status: string;
  case_id: string;
  billable: boolean;
}

interface ManualLine {
  description: string;
  quantity: number;
  unit_price_cents: number;
}

interface InvoiceCreationProps {
  accessToken: string;
  tenantId: string;
  onCreated: () => void;
  onCancel: () => void;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatEUR(cents: number): string {
  return new Intl.NumberFormat("fr-BE", {
    style: "currency",
    currency: "EUR",
  }).format(cents / 100);
}

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h${m.toString().padStart(2, "0")}` : `${m}min`;
}

function generateInvoiceNumber(): string {
  const year = new Date().getFullYear();
  const seq = String(Math.floor(Math.random() * 900) + 100);
  return `FACT-${year}-${seq}`;
}

const COMMON_LINES: { description: string; unit_price_cents: number }[] = [
  { description: "Frais de dossier", unit_price_cents: 5000 },
  { description: "Debours", unit_price_cents: 0 },
  { description: "Frais de justice", unit_price_cents: 0 },
  { description: "Frais d'huissier", unit_price_cents: 0 },
  { description: "Frais d'expertise", unit_price_cents: 0 },
];

const STEP_LABELS = [
  "Selection",
  "Prestations",
  "Lignes additionnelles",
  "Finalisation",
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function InvoiceCreation({
  accessToken,
  tenantId,
  onCreated,
  onCancel,
}: InvoiceCreationProps) {
  // --- Wizard state ---
  const [step, setStep] = useState(0);

  // --- Step 1: Selection ---
  const [cases, setCases] = useState<CaseOption[]>([]);
  const [casesLoading, setCasesLoading] = useState(true);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [contacts, setContacts] = useState<ContactOption[]>([]);
  const [contactSearch, setContactSearch] = useState("");
  const [contactSearching, setContactSearching] = useState(false);
  const [selectedContactId, setSelectedContactId] = useState("");

  // --- Step 2: Prestations ---
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([]);
  const [entriesLoading, setEntriesLoading] = useState(false);
  const [selectedEntryIds, setSelectedEntryIds] = useState<Set<string>>(
    new Set(),
  );

  // --- Step 3: Manual lines ---
  const [manualLines, setManualLines] = useState<ManualLine[]>([]);

  // --- Step 4: Finalisation ---
  const [invoiceNumber, setInvoiceNumber] = useState(generateInvoiceNumber());
  const [issueDate] = useState(new Date().toISOString().split("T")[0]);
  const [dueDate, setDueDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().split("T")[0];
  });
  const [vatRate, setVatRate] = useState(21);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // --- Load cases on mount ---
  useEffect(() => {
    apiFetch<{ items: CaseOption[] }>("/cases", accessToken, { tenantId })
      .then((data) => setCases(data.items))
      .catch(() => {})
      .finally(() => setCasesLoading(false));
  }, [accessToken, tenantId]);

  // --- Search contacts ---
  const searchContacts = useCallback(
    async (q: string) => {
      if (q.length < 2) {
        setContacts([]);
        return;
      }
      setContactSearching(true);
      try {
        const data = await apiFetch<{ items: ContactOption[] }>(
          `/contacts/search?q=${encodeURIComponent(q)}`,
          accessToken,
          { tenantId },
        );
        setContacts(data.items || []);
      } catch {
        setContacts([]);
      } finally {
        setContactSearching(false);
      }
    },
    [accessToken, tenantId],
  );

  useEffect(() => {
    const timer = setTimeout(() => {
      searchContacts(contactSearch);
    }, 300);
    return () => clearTimeout(timer);
  }, [contactSearch, searchContacts]);

  // --- Load time entries when case is selected ---
  useEffect(() => {
    if (!selectedCaseId) {
      setTimeEntries([]);
      return;
    }
    setEntriesLoading(true);
    apiFetch<{ items: TimeEntry[] }>(
      `/time-entries?case_id=${selectedCaseId}&status=approved`,
      accessToken,
      { tenantId },
    )
      .then((data) => setTimeEntries(data.items))
      .catch(() => setTimeEntries([]))
      .finally(() => setEntriesLoading(false));
  }, [selectedCaseId, accessToken, tenantId]);

  // --- Calculations ---
  const selectedEntries = timeEntries.filter((e) =>
    selectedEntryIds.has(e.id),
  );

  const timeEntriesSubtotalCents = selectedEntries.reduce((sum, e) => {
    const rate = e.hourly_rate_cents || 15000;
    return sum + Math.round((rate * e.duration_minutes) / 60);
  }, 0);

  const manualLinesSubtotalCents = manualLines.reduce(
    (sum, l) => sum + Math.round(l.quantity * l.unit_price_cents),
    0,
  );

  const subtotalHTCents = timeEntriesSubtotalCents + manualLinesSubtotalCents;
  const tvaCents = Math.round(subtotalHTCents * (vatRate / 100));
  const totalTTCCents = subtotalHTCents + tvaCents;

  // --- Toggle time entry ---
  const toggleEntry = (id: string) => {
    setSelectedEntryIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAllEntries = () => {
    if (selectedEntryIds.size === timeEntries.length) {
      setSelectedEntryIds(new Set());
    } else {
      setSelectedEntryIds(new Set(timeEntries.map((e) => e.id)));
    }
  };

  // --- Manual lines ---
  const addManualLine = (preset?: { description: string; unit_price_cents: number }) => {
    setManualLines((prev) => [
      ...prev,
      {
        description: preset?.description || "",
        quantity: 1,
        unit_price_cents: preset?.unit_price_cents || 0,
      },
    ]);
  };

  const updateManualLine = (
    index: number,
    field: keyof ManualLine,
    value: string | number,
  ) => {
    setManualLines((prev) =>
      prev.map((l, i) => (i === index ? { ...l, [field]: value } : l)),
    );
  };

  const removeManualLine = (index: number) => {
    setManualLines((prev) => prev.filter((_, i) => i !== index));
  };

  // --- Navigation ---
  const canProceed = (): boolean => {
    if (step === 0) return !!selectedCaseId && !!selectedContactId;
    if (step === 1) return true;
    if (step === 2) return true;
    if (step === 3) return !!invoiceNumber && subtotalHTCents > 0;
    return false;
  };

  // --- Submit ---
  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const lines = [
        ...selectedEntries.map((e) => ({
          description: e.description,
          quantity: 1,
          unit_price_cents: Math.round(
            ((e.hourly_rate_cents || 15000) * e.duration_minutes) / 60,
          ),
        })),
        ...manualLines
          .filter((l) => l.description && l.unit_price_cents > 0)
          .map((l) => ({
            description: l.description,
            quantity: l.quantity,
            unit_price_cents: l.unit_price_cents,
          })),
      ];

      await apiFetch("/invoices", accessToken, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          invoice_number: invoiceNumber,
          client_contact_id: selectedContactId,
          case_id: selectedCaseId,
          due_date: dueDate,
          vat_rate: vatRate,
          lines,
          time_entry_ids: Array.from(selectedEntryIds),
          notes,
        }),
      });

      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la creation de la facture.");
    } finally {
      setSubmitting(false);
    }
  };

  // --- Selected contact display name ---
  const selectedContact = contacts.find((c) => c.id === selectedContactId);
  const selectedCase = cases.find((c) => c.id === selectedCaseId);

  /* ================================================================ */
  /*  RENDER                                                           */
  /* ================================================================ */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-neutral-900">
            Nouvelle facture
          </h2>
          <p className="text-sm text-neutral-500 mt-1">
            Etape {step + 1} sur 4 — {STEP_LABELS[step]}
          </p>
        </div>
        <button
          onClick={onCancel}
          className="text-sm text-neutral-500 hover:text-neutral-700 transition-colors"
        >
          Annuler
        </button>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {STEP_LABELS.map((label, i) => (
          <div key={label} className="flex items-center gap-2 flex-1">
            <div
              className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-semibold transition-all ${
                i < step
                  ? "bg-success text-white"
                  : i === step
                    ? "bg-accent text-white"
                    : "bg-neutral-200 text-neutral-500"
              }`}
            >
              {i < step ? <Check className="w-4 h-4" /> : i + 1}
            </div>
            <span
              className={`text-xs font-medium hidden sm:inline ${
                i === step ? "text-accent" : "text-neutral-400"
              }`}
            >
              {label}
            </span>
            {i < STEP_LABELS.length - 1 && (
              <div
                className={`flex-1 h-0.5 ${
                  i < step ? "bg-success" : "bg-neutral-200"
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md text-sm">
          {error}
        </div>
      )}

      {/* Step content */}
      <Card className="border border-neutral-200">
        {/* ============ STEP 1: SELECTION ============ */}
        {step === 0 && (
          <div className="space-y-6">
            {/* Case selection */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Dossier
              </label>
              {casesLoading ? (
                <div className="flex items-center gap-2 text-sm text-neutral-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Chargement des dossiers...
                </div>
              ) : (
                <select
                  value={selectedCaseId}
                  onChange={(e) => {
                    setSelectedCaseId(e.target.value);
                    setSelectedEntryIds(new Set());
                  }}
                  className="input max-w-lg"
                >
                  <option value="">Selectionner un dossier...</option>
                  {cases.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.reference} — {c.title}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Contact search */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Client / Contact
              </label>
              <div className="relative max-w-lg">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
                <input
                  type="text"
                  value={contactSearch}
                  onChange={(e) => setContactSearch(e.target.value)}
                  placeholder="Rechercher un contact par nom ou email..."
                  className="input pl-10"
                />
                {contactSearching && (
                  <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-neutral-400" />
                )}
              </div>

              {/* Contact results */}
              {contacts.length > 0 && (
                <div className="mt-2 max-w-lg border border-neutral-200 rounded-md overflow-hidden divide-y divide-neutral-100 max-h-48 overflow-y-auto">
                  {contacts.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => {
                        setSelectedContactId(c.id);
                        setContactSearch(
                          c.company_name
                            ? `${c.first_name} ${c.last_name} (${c.company_name})`
                            : `${c.first_name} ${c.last_name}`,
                        );
                        setContacts([]);
                      }}
                      className={`w-full text-left px-4 py-2.5 text-sm hover:bg-accent-50 transition-colors ${
                        selectedContactId === c.id
                          ? "bg-accent-50 text-accent-700"
                          : "text-neutral-700"
                      }`}
                    >
                      <span className="font-medium">
                        {c.first_name} {c.last_name}
                      </span>
                      {c.company_name && (
                        <span className="text-neutral-500">
                          {" "}
                          — {c.company_name}
                        </span>
                      )}
                      <span className="block text-xs text-neutral-400">
                        {c.email}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {selectedContactId && selectedContact && (
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant="success" size="sm" dot>
                    Contact selectionne
                  </Badge>
                  <span className="text-sm text-neutral-700">
                    {selectedContact.first_name} {selectedContact.last_name}
                    {selectedContact.company_name &&
                      ` (${selectedContact.company_name})`}
                  </span>
                </div>
              )}

              {selectedContactId && !selectedContact && (
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant="success" size="sm" dot>
                    Contact selectionne
                  </Badge>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ============ STEP 2: PRESTATIONS ============ */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-neutral-900">
                  Prestations approuvees
                </h3>
                <p className="text-sm text-neutral-500 mt-0.5">
                  Selectionnez les prestations a inclure dans la facture.
                </p>
              </div>
              {timeEntries.length > 0 && (
                <span className="text-sm font-medium text-neutral-700">
                  {selectedEntryIds.size} / {timeEntries.length}{" "}
                  selectionnee(s)
                </span>
              )}
            </div>

            {entriesLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-accent" />
              </div>
            ) : timeEntries.length === 0 ? (
              <div className="text-center py-12 text-sm text-neutral-400">
                Aucune prestation approuvee pour ce dossier.
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-md border border-neutral-200 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-gradient-to-r from-neutral-50 to-neutral-100 border-b border-neutral-200">
                        <th className="w-10 px-4 py-3">
                          <input
                            type="checkbox"
                            checked={
                              timeEntries.length > 0 &&
                              selectedEntryIds.size === timeEntries.length
                            }
                            onChange={toggleAllEntries}
                            className="rounded border-neutral-300"
                          />
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                          Date
                        </th>
                        <th className="text-left px-4 py-3 text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                          Description
                        </th>
                        <th className="text-right px-4 py-3 text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                          Duree
                        </th>
                        <th className="text-right px-4 py-3 text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                          Taux/h
                        </th>
                        <th className="text-right px-4 py-3 text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                          Montant
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-100">
                      {timeEntries.map((e) => {
                        const rate = e.hourly_rate_cents || 15000;
                        const amount = Math.round(
                          (rate * e.duration_minutes) / 60,
                        );
                        return (
                          <tr
                            key={e.id}
                            className={`hover:bg-neutral-50/50 transition-all duration-200 cursor-pointer ${
                              selectedEntryIds.has(e.id) ? "bg-accent-50/30" : ""
                            }`}
                            onClick={() => toggleEntry(e.id)}
                          >
                            <td className="px-4 py-3">
                              <input
                                type="checkbox"
                                checked={selectedEntryIds.has(e.id)}
                                onChange={() => toggleEntry(e.id)}
                                onClick={(ev) => ev.stopPropagation()}
                                className="rounded border-neutral-300"
                              />
                            </td>
                            <td className="px-4 py-3 text-sm text-neutral-900">
                              {new Date(e.date).toLocaleDateString("fr-BE")}
                            </td>
                            <td className="px-4 py-3 text-sm text-neutral-700 max-w-xs truncate">
                              {e.description}
                            </td>
                            <td className="px-4 py-3 text-sm font-medium text-neutral-900 text-right">
                              {formatDuration(e.duration_minutes)}
                            </td>
                            <td className="px-4 py-3 text-sm text-neutral-600 text-right">
                              {formatEUR(rate)}
                            </td>
                            <td className="px-4 py-3 text-sm font-semibold text-neutral-900 text-right">
                              {formatEUR(amount)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                    {selectedEntryIds.size > 0 && (
                      <tfoot>
                        <tr className="bg-neutral-50 border-t border-neutral-200">
                          <td
                            colSpan={5}
                            className="px-4 py-3 text-sm font-semibold text-neutral-700 text-right"
                          >
                            Sous-total prestations
                          </td>
                          <td className="px-4 py-3 text-sm font-bold text-neutral-900 text-right">
                            {formatEUR(timeEntriesSubtotalCents)}
                          </td>
                        </tr>
                      </tfoot>
                    )}
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ============ STEP 3: LIGNES ADDITIONNELLES ============ */}
        {step === 2 && (
          <div className="space-y-4">
            <div>
              <h3 className="text-base font-semibold text-neutral-900">
                Lignes additionnelles
              </h3>
              <p className="text-sm text-neutral-500 mt-0.5">
                Ajoutez des frais supplementaires ou debours a la facture.
              </p>
            </div>

            {/* Quick-add presets */}
            <div>
              <p className="text-xs font-medium text-neutral-600 uppercase tracking-wide mb-2">
                Ajout rapide
              </p>
              <div className="flex flex-wrap gap-2">
                {COMMON_LINES.map((preset) => (
                  <button
                    key={preset.description}
                    onClick={() => addManualLine(preset)}
                    className="px-3 py-1.5 text-xs font-medium bg-neutral-100 text-neutral-700 rounded-md hover:bg-neutral-200 transition-colors"
                  >
                    + {preset.description}
                  </button>
                ))}
              </div>
            </div>

            {/* Manual lines table */}
            {manualLines.length > 0 && (
              <div className="bg-white rounded-xl shadow-md border border-neutral-200 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-gradient-to-r from-neutral-50 to-neutral-100 border-b border-neutral-200">
                        <th className="text-left px-4 py-3 text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                          Description
                        </th>
                        <th className="text-right px-4 py-3 text-xs font-semibold text-neutral-700 uppercase tracking-wider w-28">
                          Quantite
                        </th>
                        <th className="text-right px-4 py-3 text-xs font-semibold text-neutral-700 uppercase tracking-wider w-36">
                          Prix unitaire
                        </th>
                        <th className="text-right px-4 py-3 text-xs font-semibold text-neutral-700 uppercase tracking-wider w-32">
                          Total
                        </th>
                        <th className="w-12 px-2 py-3"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-100">
                      {manualLines.map((line, i) => (
                        <tr key={i} className="hover:bg-neutral-50/50">
                          <td className="px-4 py-2">
                            <input
                              type="text"
                              value={line.description}
                              onChange={(e) =>
                                updateManualLine(
                                  i,
                                  "description",
                                  e.target.value,
                                )
                              }
                              placeholder="Description..."
                              className="input text-sm"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <input
                              type="number"
                              min={1}
                              value={line.quantity}
                              onChange={(e) =>
                                updateManualLine(
                                  i,
                                  "quantity",
                                  parseInt(e.target.value) || 1,
                                )
                              }
                              className="input text-sm text-right"
                            />
                          </td>
                          <td className="px-4 py-2">
                            <input
                              type="number"
                              min={0}
                              step={0.01}
                              value={(line.unit_price_cents / 100).toFixed(2)}
                              onChange={(e) =>
                                updateManualLine(
                                  i,
                                  "unit_price_cents",
                                  Math.round(
                                    parseFloat(e.target.value || "0") * 100,
                                  ),
                                )
                              }
                              className="input text-sm text-right"
                            />
                          </td>
                          <td className="px-4 py-2 text-sm font-semibold text-neutral-900 text-right">
                            {formatEUR(
                              Math.round(line.quantity * line.unit_price_cents),
                            )}
                          </td>
                          <td className="px-2 py-2 text-center">
                            <button
                              onClick={() => removeManualLine(i)}
                              className="p-1 text-neutral-400 hover:text-danger transition-colors"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="bg-neutral-50 border-t border-neutral-200">
                        <td
                          colSpan={3}
                          className="px-4 py-3 text-sm font-semibold text-neutral-700 text-right"
                        >
                          Sous-total lignes additionnelles
                        </td>
                        <td className="px-4 py-3 text-sm font-bold text-neutral-900 text-right">
                          {formatEUR(manualLinesSubtotalCents)}
                        </td>
                        <td></td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            )}

            <button
              onClick={() => addManualLine()}
              className="flex items-center gap-2 text-sm font-medium text-accent hover:text-accent-700 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Ajouter une ligne
            </button>
          </div>
        )}

        {/* ============ STEP 4: FINALISATION ============ */}
        {step === 3 && (
          <div className="space-y-6">
            {/* Invoice details */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Numero de facture
                </label>
                <input
                  type="text"
                  value={invoiceNumber}
                  onChange={(e) => setInvoiceNumber(e.target.value)}
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Taux TVA (%)
                </label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={0.5}
                  value={vatRate}
                  onChange={(e) =>
                    setVatRate(parseFloat(e.target.value) || 0)
                  }
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Date d&apos;emission
                </label>
                <input
                  type="date"
                  value={issueDate}
                  readOnly
                  className="input bg-neutral-50 text-neutral-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Date d&apos;echeance
                </label>
                <input
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  className="input"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Notes
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Remarques ou conditions particulieres..."
                  className="input"
                  rows={3}
                />
              </div>
            </div>

            {/* Summary */}
            <div className="bg-gradient-to-br from-neutral-50 to-white border border-neutral-200 rounded-xl p-6">
              <h4 className="text-sm font-semibold text-neutral-700 uppercase tracking-wide mb-4">
                Recapitulatif
              </h4>

              {/* Case & contact info */}
              <div className="grid grid-cols-2 gap-4 mb-4 pb-4 border-b border-neutral-200">
                <div>
                  <p className="text-xs text-neutral-500">Dossier</p>
                  <p className="text-sm font-medium text-neutral-900">
                    {selectedCase
                      ? `${selectedCase.reference} — ${selectedCase.title}`
                      : "—"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-neutral-500">Contact</p>
                  <p className="text-sm font-medium text-neutral-900">
                    {selectedContact
                      ? `${selectedContact.first_name} ${selectedContact.last_name}`
                      : "—"}
                  </p>
                </div>
              </div>

              {/* Line items summary */}
              {selectedEntries.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs text-neutral-500 mb-1">
                    {selectedEntries.length} prestation(s)
                  </p>
                  <div className="flex justify-between text-sm">
                    <span className="text-neutral-600">Prestations</span>
                    <span className="font-medium text-neutral-900">
                      {formatEUR(timeEntriesSubtotalCents)}
                    </span>
                  </div>
                </div>
              )}

              {manualLines.filter((l) => l.description).length > 0 && (
                <div className="mb-3">
                  <p className="text-xs text-neutral-500 mb-1">
                    {manualLines.filter((l) => l.description).length} ligne(s)
                    additionnelle(s)
                  </p>
                  <div className="flex justify-between text-sm">
                    <span className="text-neutral-600">
                      Lignes additionnelles
                    </span>
                    <span className="font-medium text-neutral-900">
                      {formatEUR(manualLinesSubtotalCents)}
                    </span>
                  </div>
                </div>
              )}

              <div className="border-t border-neutral-200 pt-3 mt-3 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-600">Sous-total HT</span>
                  <span className="font-medium text-neutral-900">
                    {formatEUR(subtotalHTCents)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-600">TVA ({vatRate}%)</span>
                  <span className="font-medium text-neutral-900">
                    {formatEUR(tvaCents)}
                  </span>
                </div>
                <div className="flex justify-between text-lg font-bold border-t border-neutral-300 pt-2 mt-2">
                  <span className="text-neutral-900">Total TTC</span>
                  <span className="text-accent">{formatEUR(totalTTCCents)}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Navigation buttons */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => (step === 0 ? onCancel() : setStep(step - 1))}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          {step === 0 ? "Annuler" : "Precedent"}
        </button>

        {step < 3 ? (
          <button
            onClick={() => setStep(step + 1)}
            disabled={!canProceed()}
            className="btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            Suivant
            <ChevronRight className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={submitting || !canProceed()}
            className="btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Creation en cours...
              </>
            ) : (
              <>
                <FileText className="w-4 h-4" />
                Creer la facture
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
