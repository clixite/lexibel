"use client";

import { useSession } from "next-auth/react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState, useCallback, useRef } from "react";
import { apiFetch } from "@/lib/api";
import {
  Loader2,
  ArrowLeft,
  FileText,
  Users,
  FolderOpen,
  Clock,
  CalendarClock,
  Search,
  Plus,
  X,
  Check,
  Link2,
  FileIcon,
  FileImage,
  FileSpreadsheet,
  FileVideo,
  FileAudio,
  File,
  ChevronDown,
  AlertCircle,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface CaseData {
  id: string;
  reference: string;
  court_reference: string | null;
  title: string;
  matter_type: string;
  status: string;
  jurisdiction: string | null;
  responsible_user_id: string | null;
  opened_at: string;
  closed_at: string | null;
  metadata: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

interface CaseContact {
  id: string;
  full_name: string;
  type: string;
  email: string | null;
  phone_e164: string | null;
  role: string;
}

interface SearchContact {
  id: string;
  full_name: string;
  type: string;
  email: string | null;
}

interface EvidenceLink {
  file_name: string;
  mime_type: string;
  file_size_bytes: number;
}

interface TimelineEvent {
  id: string;
  source: string;
  event_type: string;
  title: string;
  body: string | null;
  occurred_at: string;
  created_by: string | null;
  evidence_links: EvidenceLink[];
}

interface TimeEntry {
  id: string;
  description: string;
  duration_minutes: number;
  billable: boolean;
  date: string;
  status: string;
  hourly_rate_cents: number | null;
}

type TabId = "resume" | "contacts" | "documents" | "prestations" | "timeline";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "open", label: "Ouvert" },
  { value: "in_progress", label: "En cours" },
  { value: "pending", label: "En attente" },
  { value: "closed", label: "Fermé" },
  { value: "archived", label: "Archivé" },
];

const STATUS_STYLES: Record<string, string> = {
  open: "bg-success-50 text-success-700 border-success-200",
  in_progress: "bg-accent-50 text-accent-700 border-accent-200",
  pending: "bg-warning-50 text-warning-700 border-warning-200",
  closed: "bg-neutral-100 text-neutral-600 border-neutral-300",
  archived: "bg-neutral-100 text-neutral-500 border-neutral-300",
};

const MATTER_TYPES: { value: string; label: string }[] = [
  { value: "general", label: "Général" },
  { value: "civil", label: "Civil" },
  { value: "penal", label: "Pénal" },
  { value: "commercial", label: "Commercial" },
  { value: "social", label: "Social" },
  { value: "fiscal", label: "Fiscal" },
  { value: "family", label: "Familial" },
  { value: "administrative", label: "Administratif" },
];

const CONTACT_ROLES: { value: string; label: string }[] = [
  { value: "client", label: "Client" },
  { value: "adverse", label: "Partie adverse" },
  { value: "witness", label: "Témoin" },
  { value: "third_party", label: "Tiers" },
];

const EVENT_TYPES: { value: string; label: string }[] = [
  { value: "note", label: "Note" },
  { value: "hearing", label: "Audience" },
  { value: "meeting", label: "Réunion" },
  { value: "filing", label: "Dépôt de pièces" },
  { value: "judgment", label: "Jugement" },
  { value: "correspondence", label: "Correspondance" },
  { value: "phone_call", label: "Appel téléphonique" },
  { value: "other", label: "Autre" },
];

const TIME_STATUS_STYLES: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-700",
  submitted: "bg-accent-50 text-accent-700",
  approved: "bg-success-50 text-success-700",
  invoiced: "bg-warning-50 text-warning-700",
};

const TIME_STATUS_LABELS: Record<string, string> = {
  draft: "Brouillon",
  submitted: "Soumis",
  approved: "Approuvé",
  invoiced: "Facturé",
};

const SOURCE_COLORS: Record<string, string> = {
  MANUAL: "bg-accent",
  EMAIL: "bg-success",
  SYSTEM: "bg-neutral-400",
  IMPORT: "bg-warning",
  AI: "bg-danger",
};

const TABS: { id: TabId; label: string; icon: typeof FileText }[] = [
  { id: "resume", label: "Résumé", icon: FileText },
  { id: "contacts", label: "Contacts", icon: Users },
  { id: "documents", label: "Documents", icon: FolderOpen },
  { id: "prestations", label: "Prestations", icon: Clock },
  { id: "timeline", label: "Chronologie", icon: CalendarClock },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function statusLabel(status: string): string {
  return STATUS_OPTIONS.find((s) => s.value === status)?.label ?? status;
}

function matterLabel(mt: string): string {
  return MATTER_TYPES.find((m) => m.value === mt)?.label ?? mt;
}

function roleLabel(role: string): string {
  return CONTACT_ROLES.find((r) => r.value === role)?.label ?? role;
}

function eventTypeLabel(et: string): string {
  return EVENT_TYPES.find((e) => e.value === et)?.label ?? et;
}

function fmtDate(d: string | null): string {
  if (!d) return "\u2014";
  return new Date(d).toLocaleDateString("fr-BE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function fmtDateLong(d: string | null): string {
  if (!d) return "\u2014";
  return new Date(d).toLocaleDateString("fr-BE", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}min`;
  if (m === 0) return `${h}h`;
  return `${h}h${m.toString().padStart(2, "0")}`;
}

function fmtFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

function fileIcon(mime: string) {
  if (mime.startsWith("image/")) return FileImage;
  if (mime.includes("spreadsheet") || mime.includes("excel"))
    return FileSpreadsheet;
  if (mime.includes("pdf") || mime.includes("document")) return FileIcon;
  if (mime.startsWith("video/")) return FileVideo;
  if (mime.startsWith("audio/")) return FileAudio;
  return File;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function CaseDetailPage() {
  const { data: session, status: sessionStatus } = useSession();
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;

  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;

  /* ---------- core state ---------- */
  const [caseData, setCaseData] = useState<CaseData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("resume");

  /* ---------- tab data ---------- */
  const [contacts, setContacts] = useState<CaseContact[]>([]);
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [tabLoading, setTabLoading] = useState(false);

  /* ---------- inline edit ---------- */
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [saving, setSaving] = useState(false);

  /* ---------- contact link modal ---------- */
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [contactSearch, setContactSearch] = useState("");
  const [searchResults, setSearchResults] = useState<SearchContact[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedContact, setSelectedContact] = useState<SearchContact | null>(
    null,
  );
  const [linkRole, setLinkRole] = useState("client");
  const [linking, setLinking] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* ---------- time entry form ---------- */
  const [showTimeForm, setShowTimeForm] = useState(false);
  const [timeForm, setTimeForm] = useState({
    description: "",
    duration_minutes: 30,
    billable: true,
    date: new Date().toISOString().split("T")[0],
  });
  const [timeSubmitting, setTimeSubmitting] = useState(false);

  /* ---------- event form ---------- */
  const [showEventForm, setShowEventForm] = useState(false);
  const [eventForm, setEventForm] = useState({
    event_type: "note",
    title: "",
    body: "",
    occurred_at: new Date().toISOString().slice(0, 16),
  });
  const [eventSubmitting, setEventSubmitting] = useState(false);

  /* ---------------------------------------------------------------- */
  /*  Data fetching                                                    */
  /* ---------------------------------------------------------------- */

  const fetchCase = useCallback(async () => {
    if (!token || !tenantId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await apiFetch<CaseData>(`/cases/${caseId}`, token, {
        tenantId,
      });
      setCaseData(data);
    } catch (err: any) {
      setError(err.message || "Erreur lors du chargement du dossier");
    } finally {
      setLoading(false);
    }
  }, [token, tenantId, caseId]);

  const fetchContacts = useCallback(async () => {
    if (!token || !tenantId) return;
    setTabLoading(true);
    try {
      const data = await apiFetch<{ items: CaseContact[] }>(
        `/cases/${caseId}/contacts`,
        token,
        { tenantId },
      );
      setContacts(data.items);
    } catch {
      /* silently fail for tab data */
    } finally {
      setTabLoading(false);
    }
  }, [token, tenantId, caseId]);

  const fetchTimeEntries = useCallback(async () => {
    if (!token || !tenantId) return;
    setTabLoading(true);
    try {
      const data = await apiFetch<{ items: TimeEntry[] }>(
        `/time-entries?case_id=${caseId}`,
        token,
        { tenantId },
      );
      setTimeEntries(data.items);
    } catch {
      /* silently fail */
    } finally {
      setTabLoading(false);
    }
  }, [token, tenantId, caseId]);

  const fetchTimeline = useCallback(async () => {
    if (!token || !tenantId) return;
    setTabLoading(true);
    try {
      const data = await apiFetch<{ items: TimelineEvent[] }>(
        `/cases/${caseId}/timeline`,
        token,
        { tenantId },
      );
      setTimeline(data.items);
    } catch {
      /* silently fail */
    } finally {
      setTabLoading(false);
    }
  }, [token, tenantId, caseId]);

  useEffect(() => {
    if (token && tenantId) fetchCase();
  }, [fetchCase, token, tenantId]);

  useEffect(() => {
    if (!token || !tenantId || !caseData) return;
    if (activeTab === "contacts") fetchContacts();
    else if (activeTab === "prestations") fetchTimeEntries();
    else if (activeTab === "timeline") fetchTimeline();
    // documents are derived from timeline
    else if (activeTab === "documents" && timeline.length === 0) fetchTimeline();
  }, [
    activeTab,
    token,
    tenantId,
    caseData,
    fetchContacts,
    fetchTimeEntries,
    fetchTimeline,
    timeline.length,
  ]);

  /* ---------------------------------------------------------------- */
  /*  Inline PATCH helpers                                             */
  /* ---------------------------------------------------------------- */

  const patchCase = async (body: Record<string, any>) => {
    if (!token || !tenantId) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await apiFetch<CaseData>(`/cases/${caseId}`, token, {
        tenantId,
        method: "PATCH",
        body: JSON.stringify(body),
      });
      setCaseData(updated);
      flash("Modification enregistrée");
    } catch (err: any) {
      setError(err.message || "Erreur lors de la sauvegarde");
    } finally {
      setSaving(false);
      setEditingField(null);
    }
  };

  const handleStatusChange = (newStatus: string) => {
    if (!caseData || newStatus === caseData.status) return;
    const body: Record<string, any> = { status: newStatus };
    if (newStatus === "closed" && !caseData.closed_at) {
      body.closed_at = new Date().toISOString();
    }
    patchCase(body);
  };

  const startEdit = (field: string, currentValue: string) => {
    setEditingField(field);
    setEditValue(currentValue);
  };

  const commitEdit = (field: string) => {
    if (!caseData) return;
    const trimmed = editValue.trim();

    if (field === "description") {
      const currentDesc =
        (caseData.metadata && caseData.metadata.description) || "";
      if (trimmed === currentDesc) {
        setEditingField(null);
        return;
      }
      patchCase({
        metadata: { ...(caseData.metadata || {}), description: trimmed },
      });
      // Optimistically update local metadata for the description field
      // (actual update comes from patchCase setCaseData)
      return;
    }

    const currentVal = (caseData as any)[field] ?? "";
    if (trimmed === currentVal) {
      setEditingField(null);
      return;
    }
    patchCase({ [field]: trimmed || null });
  };

  /* ---------------------------------------------------------------- */
  /*  Contact search & link                                            */
  /* ---------------------------------------------------------------- */

  const searchContacts = (query: string) => {
    setContactSearch(query);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }
    searchTimer.current = setTimeout(async () => {
      if (!token || !tenantId) return;
      setSearchLoading(true);
      try {
        const data = await apiFetch<{ items: SearchContact[] }>(
          `/contacts?q=${encodeURIComponent(query)}`,
          token,
          { tenantId },
        );
        setSearchResults(data.items);
      } catch {
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 350);
  };

  const linkContact = async () => {
    if (!token || !tenantId || !selectedContact) return;
    setLinking(true);
    setError(null);
    try {
      await apiFetch(`/cases/${caseId}/contacts`, token, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          contact_id: selectedContact.id,
          role: linkRole,
        }),
      });
      flash(`${selectedContact.full_name} lié(e) au dossier`);
      setShowLinkModal(false);
      setSelectedContact(null);
      setContactSearch("");
      setSearchResults([]);
      setLinkRole("client");
      fetchContacts();
    } catch (err: any) {
      setError(err.message || "Erreur lors de la liaison du contact");
    } finally {
      setLinking(false);
    }
  };

  /* ---------------------------------------------------------------- */
  /*  Time entry creation                                              */
  /* ---------------------------------------------------------------- */

  const submitTimeEntry = async () => {
    if (!token || !tenantId || !timeForm.description.trim()) return;
    setTimeSubmitting(true);
    setError(null);
    try {
      await apiFetch("/time-entries", token, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          case_id: caseId,
          description: timeForm.description,
          duration_minutes: timeForm.duration_minutes,
          billable: timeForm.billable,
          date: timeForm.date,
          source: "MANUAL",
          status: "draft",
        }),
      });
      flash("Prestation enregistrée");
      setShowTimeForm(false);
      setTimeForm({
        description: "",
        duration_minutes: 30,
        billable: true,
        date: new Date().toISOString().split("T")[0],
      });
      fetchTimeEntries();
    } catch (err: any) {
      setError(err.message || "Erreur lors de l\u2019enregistrement");
    } finally {
      setTimeSubmitting(false);
    }
  };

  /* ---------------------------------------------------------------- */
  /*  Event creation                                                   */
  /* ---------------------------------------------------------------- */

  const submitEvent = async () => {
    if (!token || !tenantId || !eventForm.title.trim()) return;
    setEventSubmitting(true);
    setError(null);
    try {
      await apiFetch(`/cases/${caseId}/events`, token, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          source: "MANUAL",
          event_type: eventForm.event_type,
          title: eventForm.title,
          body: eventForm.body || undefined,
          occurred_at: new Date(eventForm.occurred_at).toISOString(),
        }),
      });
      flash("Événement ajouté");
      setShowEventForm(false);
      setEventForm({
        event_type: "note",
        title: "",
        body: "",
        occurred_at: new Date().toISOString().slice(0, 16),
      });
      fetchTimeline();
    } catch (err: any) {
      setError(err.message || "Erreur lors de l\u2019ajout de l\u2019événement");
    } finally {
      setEventSubmitting(false);
    }
  };

  /* ---------------------------------------------------------------- */
  /*  Toasts                                                           */
  /* ---------------------------------------------------------------- */

  const flash = (msg: string) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(null), 3000);
  };

  /* ---------------------------------------------------------------- */
  /*  Derived data                                                     */
  /* ---------------------------------------------------------------- */

  const allDocuments: (EvidenceLink & { eventTitle: string; eventDate: string })[] =
    timeline.flatMap((ev) =>
      ev.evidence_links.map((link) => ({
        ...link,
        eventTitle: ev.title,
        eventDate: ev.occurred_at,
      })),
    );

  /* ---------------------------------------------------------------- */
  /*  Loading / error states                                           */
  /* ---------------------------------------------------------------- */

  if (sessionStatus === "loading" || loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  if (error && !caseData) {
    return (
      <div className="p-6">
        <button
          onClick={() => router.push("/dashboard/cases")}
          className="inline-flex items-center gap-2 text-neutral-600 hover:text-neutral-900 mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Retour aux dossiers
        </button>
        <div className="card border border-danger-200 bg-danger-50">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-danger" />
            <p className="text-danger-700">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="p-6">
        <div className="card">
          <p className="text-neutral-600">Dossier introuvable.</p>
        </div>
      </div>
    );
  }

  const description =
    (caseData.metadata && caseData.metadata.description) || "";

  /* ================================================================ */
  /*  RENDER                                                          */
  /* ================================================================ */

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* ---------- success toast ---------- */}
      {success && (
        <div className="fixed top-4 right-4 z-50 bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-md text-sm flex items-center gap-2 shadow-lg">
          <Check className="w-4 h-4" />
          {success}
        </div>
      )}

      {/* ---------- error banner ---------- */}
      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-auto text-danger-400 hover:text-danger-600"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* ============================================================ */}
      {/*  HEADER                                                       */}
      {/* ============================================================ */}
      <div className="flex items-start gap-4">
        <button
          onClick={() => router.push("/dashboard/cases")}
          className="mt-1.5 text-neutral-500 hover:text-neutral-900 transition-colors"
          aria-label="Retour aux dossiers"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-3 mb-1">
            {/* reference badge */}
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent-50 text-accent-700 tracking-wide">
              {caseData.reference}
            </span>

            <h1 className="text-2xl font-bold text-neutral-900 truncate">
              {caseData.title}
            </h1>

            {/* status dropdown */}
            <div className="relative inline-block">
              <select
                value={caseData.status}
                onChange={(e) => handleStatusChange(e.target.value)}
                disabled={saving}
                className={`appearance-none cursor-pointer pl-3 pr-7 py-1 text-xs font-medium rounded-full border transition-colors focus:outline-none focus:ring-2 focus:ring-accent/40 ${
                  STATUS_STYLES[caseData.status] ??
                  "bg-neutral-100 text-neutral-600 border-neutral-300"
                } ${saving ? "opacity-50 cursor-wait" : ""}`}
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3" />
            </div>

            {/* matter_type tag */}
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-neutral-100 text-neutral-700">
              {matterLabel(caseData.matter_type)}
            </span>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/*  TABS                                                         */}
      {/* ============================================================ */}
      <div className="border-b border-neutral-200">
        <nav className="flex gap-6 -mb-px" aria-label="Onglets du dossier">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-1 py-3 text-sm font-medium border-b-2 transition-colors ${
                  active
                    ? "border-accent text-accent"
                    : "border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300"
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* ============================================================ */}
      {/*  TAB CONTENT                                                  */}
      {/* ============================================================ */}
      <div className="min-h-[420px]">
        {/* ---------------------------------------------------------- */}
        {/*  TAB 1 : Résumé                                             */}
        {/* ---------------------------------------------------------- */}
        {activeTab === "resume" && (
          <div className="card">
            <h2 className="text-lg font-semibold text-neutral-900 mb-6">
              Informations générales
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-5">
              {/* reference (read-only) */}
              <InlineField label="Référence" readOnly value={caseData.reference} />

              {/* title */}
              <InlineField
                label="Titre"
                value={caseData.title}
                editing={editingField === "title"}
                editValue={editValue}
                saving={saving}
                onStartEdit={() => startEdit("title", caseData.title)}
                onChangeEdit={setEditValue}
                onCommit={() => commitEdit("title")}
                onCancel={() => setEditingField(null)}
              />

              {/* matter_type */}
              <InlineFieldSelect
                label="Type d\u2019affaire"
                value={matterLabel(caseData.matter_type)}
                editing={editingField === "matter_type"}
                editValue={editValue}
                saving={saving}
                options={MATTER_TYPES}
                onStartEdit={() =>
                  startEdit("matter_type", caseData.matter_type)
                }
                onChangeEdit={setEditValue}
                onCommit={() => commitEdit("matter_type")}
                onCancel={() => setEditingField(null)}
              />

              {/* jurisdiction */}
              <InlineField
                label="Juridiction"
                value={caseData.jurisdiction || ""}
                placeholder="Non spécifiée"
                editing={editingField === "jurisdiction"}
                editValue={editValue}
                saving={saving}
                onStartEdit={() =>
                  startEdit("jurisdiction", caseData.jurisdiction || "")
                }
                onChangeEdit={setEditValue}
                onCommit={() => commitEdit("jurisdiction")}
                onCancel={() => setEditingField(null)}
              />

              {/* court_reference */}
              <InlineField
                label="Référence tribunal"
                value={caseData.court_reference || ""}
                placeholder="Non spécifiée"
                editing={editingField === "court_reference"}
                editValue={editValue}
                saving={saving}
                onStartEdit={() =>
                  startEdit(
                    "court_reference",
                    caseData.court_reference || "",
                  )
                }
                onChangeEdit={setEditValue}
                onCommit={() => commitEdit("court_reference")}
                onCancel={() => setEditingField(null)}
              />

              {/* opened_at (read-only display, not editable inline) */}
              <InlineField
                label="Date d\u2019ouverture"
                readOnly
                value={fmtDate(caseData.opened_at)}
              />

              {/* closed_at */}
              <InlineField
                label="Date de cl\u00f4ture"
                value={caseData.closed_at ? caseData.closed_at.split("T")[0] : ""}
                placeholder="Non cl\u00f4turé"
                editing={editingField === "closed_at"}
                editValue={editValue}
                saving={saving}
                inputType="date"
                onStartEdit={() =>
                  startEdit(
                    "closed_at",
                    caseData.closed_at
                      ? caseData.closed_at.split("T")[0]
                      : "",
                  )
                }
                onChangeEdit={setEditValue}
                onCommit={() => commitEdit("closed_at")}
                onCancel={() => setEditingField(null)}
              />

              {/* description (full width) */}
              <div className="md:col-span-2">
                <InlineField
                  label="Description"
                  value={description}
                  placeholder="Aucune description"
                  editing={editingField === "description"}
                  editValue={editValue}
                  saving={saving}
                  multiline
                  onStartEdit={() => startEdit("description", description)}
                  onChangeEdit={setEditValue}
                  onCommit={() => commitEdit("description")}
                  onCancel={() => setEditingField(null)}
                />
              </div>
            </div>

            {/* metadata footer */}
            <div className="mt-8 pt-6 border-t border-neutral-200">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-neutral-500 mb-1">Créé le</p>
                  <p className="text-neutral-900">
                    {fmtDateLong(caseData.created_at)}
                  </p>
                </div>
                <div>
                  <p className="text-neutral-500 mb-1">Modifié le</p>
                  <p className="text-neutral-900">
                    {fmtDateLong(caseData.updated_at)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ---------------------------------------------------------- */}
        {/*  TAB 2 : Contacts                                           */}
        {/* ---------------------------------------------------------- */}
        {activeTab === "contacts" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-neutral-900">
                Contacts liés
              </h2>
              <button
                onClick={() => setShowLinkModal(true)}
                className="btn-primary flex items-center gap-2"
              >
                <Link2 className="w-4 h-4" />
                Lier un contact
              </button>
            </div>

            {tabLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-accent" />
              </div>
            ) : contacts.length === 0 ? (
              <div className="card text-center py-12">
                <Users className="w-12 h-12 mx-auto mb-4 text-neutral-300" />
                <p className="text-neutral-500 font-medium">
                  Aucun contact lié à ce dossier
                </p>
                <p className="text-neutral-400 text-sm mt-1">
                  Utilisez le bouton ci-dessus pour lier un contact existant.
                </p>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-subtle overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-neutral-200">
                      <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Nom
                      </th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Type
                      </th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        R\u00f4le
                      </th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Email
                      </th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Téléphone
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100">
                    {contacts.map((c) => (
                      <tr
                        key={c.id}
                        className="hover:bg-neutral-50 transition-colors"
                      >
                        <td className="px-6 py-4 text-sm font-medium text-neutral-900">
                          {c.full_name}
                        </td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-neutral-100 text-neutral-600">
                            {c.type === "natural"
                              ? "Physique"
                              : c.type === "legal"
                                ? "Morale"
                                : c.type}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-accent-50 text-accent-700">
                            {roleLabel(c.role)}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-neutral-600">
                          {c.email || "\u2014"}
                        </td>
                        <td className="px-6 py-4 text-sm text-neutral-600">
                          {c.phone_e164 || "\u2014"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* ---- Link Contact Modal ---- */}
            {showLinkModal && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 p-6">
                  <div className="flex items-center justify-between mb-5">
                    <h2 className="text-lg font-semibold text-neutral-900">
                      Lier un contact
                    </h2>
                    <button
                      onClick={() => {
                        setShowLinkModal(false);
                        setSelectedContact(null);
                        setContactSearch("");
                        setSearchResults([]);
                      }}
                      className="text-neutral-400 hover:text-neutral-600"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  {/* search */}
                  <div className="relative mb-4">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
                    <input
                      type="text"
                      placeholder="Rechercher un contact par nom..."
                      value={contactSearch}
                      onChange={(e) => searchContacts(e.target.value)}
                      className="input pl-9 w-full"
                      autoFocus
                    />
                  </div>

                  {/* results */}
                  <div className="max-h-48 overflow-y-auto border border-neutral-200 rounded-md mb-4">
                    {searchLoading ? (
                      <div className="flex items-center justify-center py-6">
                        <Loader2 className="w-5 h-5 animate-spin text-accent" />
                      </div>
                    ) : searchResults.length === 0 ? (
                      <div className="py-6 text-center text-sm text-neutral-400">
                        {contactSearch.length >= 2
                          ? "Aucun contact trouvé"
                          : "Saisissez au moins 2 caractères"}
                      </div>
                    ) : (
                      searchResults.map((sc) => (
                        <button
                          key={sc.id}
                          onClick={() => setSelectedContact(sc)}
                          className={`w-full text-left px-4 py-3 flex items-center justify-between hover:bg-neutral-50 transition-colors border-b border-neutral-100 last:border-b-0 ${
                            selectedContact?.id === sc.id
                              ? "bg-accent-50"
                              : ""
                          }`}
                        >
                          <div>
                            <p className="text-sm font-medium text-neutral-900">
                              {sc.full_name}
                            </p>
                            <p className="text-xs text-neutral-500">
                              {sc.email || "Pas d\u2019email"} \u00b7{" "}
                              {sc.type === "natural"
                                ? "Physique"
                                : sc.type === "legal"
                                  ? "Morale"
                                  : sc.type}
                            </p>
                          </div>
                          {selectedContact?.id === sc.id && (
                            <Check className="w-4 h-4 text-accent" />
                          )}
                        </button>
                      ))
                    )}
                  </div>

                  {/* role select */}
                  {selectedContact && (
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        R\u00f4le dans le dossier
                      </label>
                      <select
                        value={linkRole}
                        onChange={(e) => setLinkRole(e.target.value)}
                        className="input w-full"
                      >
                        {CONTACT_ROLES.map((r) => (
                          <option key={r.value} value={r.value}>
                            {r.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {/* actions */}
                  <div className="flex justify-end gap-3">
                    <button
                      onClick={() => {
                        setShowLinkModal(false);
                        setSelectedContact(null);
                        setContactSearch("");
                        setSearchResults([]);
                      }}
                      className="btn-secondary"
                    >
                      Annuler
                    </button>
                    <button
                      onClick={linkContact}
                      disabled={!selectedContact || linking}
                      className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {linking && (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      )}
                      Lier
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ---------------------------------------------------------- */}
        {/*  TAB 3 : Documents                                          */}
        {/* ---------------------------------------------------------- */}
        {activeTab === "documents" && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-neutral-900">
              Documents
            </h2>

            {tabLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-accent" />
              </div>
            ) : allDocuments.length === 0 ? (
              <div className="card text-center py-12">
                <FolderOpen className="w-12 h-12 mx-auto mb-4 text-neutral-300" />
                <p className="text-neutral-500 font-medium">
                  Aucun document dans ce dossier
                </p>
                <p className="text-neutral-400 text-sm mt-1">
                  Les documents apparaissent lorsque des pièces sont jointes aux
                  événements de la chronologie.
                </p>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-subtle overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-neutral-200">
                      <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Fichier
                      </th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Type
                      </th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Taille
                      </th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Événement
                      </th>
                      <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Date
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100">
                    {allDocuments.map((doc, idx) => {
                      const Icon = fileIcon(doc.mime_type);
                      return (
                        <tr
                          key={`${doc.file_name}-${idx}`}
                          className="hover:bg-neutral-50 transition-colors"
                        >
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-3">
                              <Icon className="w-5 h-5 text-accent flex-shrink-0" />
                              <span className="text-sm font-medium text-neutral-900 truncate max-w-xs">
                                {doc.file_name}
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-sm text-neutral-600">
                            {doc.mime_type}
                          </td>
                          <td className="px-6 py-4 text-sm text-neutral-600">
                            {fmtFileSize(doc.file_size_bytes)}
                          </td>
                          <td className="px-6 py-4 text-sm text-neutral-600 truncate max-w-xs">
                            {doc.eventTitle}
                          </td>
                          <td className="px-6 py-4 text-sm text-neutral-500">
                            {fmtDate(doc.eventDate)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ---------------------------------------------------------- */}
        {/*  TAB 4 : Prestations                                        */}
        {/* ---------------------------------------------------------- */}
        {activeTab === "prestations" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-neutral-900">
                Prestations
              </h2>
              <button
                onClick={() => setShowTimeForm(true)}
                className="btn-primary flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Ajouter
              </button>
            </div>

            {/* inline form */}
            {showTimeForm && (
              <div className="card border border-accent-200">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-neutral-900">
                    Nouvelle prestation
                  </h3>
                  <button
                    onClick={() => setShowTimeForm(false)}
                    className="text-neutral-400 hover:text-neutral-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-neutral-700 mb-1">
                      Date
                    </label>
                    <input
                      type="date"
                      value={timeForm.date}
                      onChange={(e) =>
                        setTimeForm((f) => ({ ...f, date: e.target.value }))
                      }
                      className="input w-full"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-xs font-medium text-neutral-700 mb-1">
                      Description
                    </label>
                    <input
                      type="text"
                      value={timeForm.description}
                      onChange={(e) =>
                        setTimeForm((f) => ({
                          ...f,
                          description: e.target.value,
                        }))
                      }
                      placeholder="Décrivez la prestation..."
                      className="input w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-neutral-700 mb-1">
                      Durée (min)
                    </label>
                    <input
                      type="number"
                      min={1}
                      value={timeForm.duration_minutes}
                      onChange={(e) =>
                        setTimeForm((f) => ({
                          ...f,
                          duration_minutes: parseInt(e.target.value) || 0,
                        }))
                      }
                      className="input w-full"
                    />
                  </div>
                </div>
                <div className="flex items-center justify-between mt-4">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={timeForm.billable}
                      onChange={(e) =>
                        setTimeForm((f) => ({
                          ...f,
                          billable: e.target.checked,
                        }))
                      }
                      className="w-4 h-4 text-accent rounded border-neutral-300"
                    />
                    <span className="text-neutral-700">Facturable</span>
                  </label>
                  <button
                    onClick={submitTimeEntry}
                    disabled={
                      timeSubmitting || !timeForm.description.trim()
                    }
                    className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {timeSubmitting && (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    )}
                    Enregistrer
                  </button>
                </div>
              </div>
            )}

            {tabLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-accent" />
              </div>
            ) : timeEntries.length === 0 && !showTimeForm ? (
              <div className="card text-center py-12">
                <Clock className="w-12 h-12 mx-auto mb-4 text-neutral-300" />
                <p className="text-neutral-500 font-medium">
                  Aucune prestation enregistrée
                </p>
                <p className="text-neutral-400 text-sm mt-1">
                  Ajoutez une prestation pour suivre le temps passé sur ce
                  dossier.
                </p>
              </div>
            ) : (
              timeEntries.length > 0 && (
                <div className="bg-white rounded-lg shadow-subtle overflow-hidden">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-neutral-200">
                        <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                          Date
                        </th>
                        <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                          Description
                        </th>
                        <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                          Durée
                        </th>
                        <th className="text-right px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                          Taux
                        </th>
                        <th className="text-right px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                          Montant
                        </th>
                        <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                          Statut
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-neutral-100">
                      {timeEntries.map((entry) => {
                        const rate = entry.hourly_rate_cents
                          ? (entry.hourly_rate_cents / 100).toFixed(2)
                          : "\u2014";
                        const amount =
                          entry.hourly_rate_cents && entry.duration_minutes
                            ? (
                                (entry.hourly_rate_cents / 100) *
                                (entry.duration_minutes / 60)
                              ).toFixed(2)
                            : "\u2014";
                        return (
                          <tr
                            key={entry.id}
                            className="hover:bg-neutral-50 transition-colors"
                          >
                            <td className="px-6 py-4 text-sm text-neutral-900">
                              {fmtDate(entry.date)}
                            </td>
                            <td className="px-6 py-4 text-sm text-neutral-700 max-w-xs truncate">
                              {entry.description}
                            </td>
                            <td className="px-6 py-4 text-sm font-medium text-neutral-900">
                              {fmtDuration(entry.duration_minutes)}
                            </td>
                            <td className="px-6 py-4 text-sm text-neutral-600 text-right">
                              {rate !== "\u2014" ? `${rate}\u00a0\u20ac/h` : rate}
                            </td>
                            <td className="px-6 py-4 text-sm font-medium text-neutral-900 text-right">
                              {amount !== "\u2014"
                                ? `${amount}\u00a0\u20ac`
                                : amount}
                            </td>
                            <td className="px-6 py-4">
                              <span
                                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                  TIME_STATUS_STYLES[entry.status] ??
                                  "bg-neutral-100 text-neutral-700"
                                }`}
                              >
                                {TIME_STATUS_LABELS[entry.status] ??
                                  entry.status}
                              </span>
                              {entry.billable && (
                                <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-success-50 text-success-700">
                                  Facturable
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )
            )}
          </div>
        )}

        {/* ---------------------------------------------------------- */}
        {/*  TAB 5 : Timeline / Chronologie                             */}
        {/* ---------------------------------------------------------- */}
        {activeTab === "timeline" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-neutral-900">
                Chronologie
              </h2>
              <button
                onClick={() => setShowEventForm(true)}
                className="btn-primary flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Ajouter un événement
              </button>
            </div>

            {/* inline event form */}
            {showEventForm && (
              <div className="card border border-accent-200">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-neutral-900">
                    Nouvel événement
                  </h3>
                  <button
                    onClick={() => setShowEventForm(false)}
                    className="text-neutral-400 hover:text-neutral-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-neutral-700 mb-1">
                      Type
                    </label>
                    <select
                      value={eventForm.event_type}
                      onChange={(e) =>
                        setEventForm((f) => ({
                          ...f,
                          event_type: e.target.value,
                        }))
                      }
                      className="input w-full"
                    >
                      {EVENT_TYPES.map((et) => (
                        <option key={et.value} value={et.value}>
                          {et.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-neutral-700 mb-1">
                      Titre
                    </label>
                    <input
                      type="text"
                      value={eventForm.title}
                      onChange={(e) =>
                        setEventForm((f) => ({
                          ...f,
                          title: e.target.value,
                        }))
                      }
                      placeholder="Titre de l\u2019événement"
                      className="input w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-neutral-700 mb-1">
                      Date & heure
                    </label>
                    <input
                      type="datetime-local"
                      value={eventForm.occurred_at}
                      onChange={(e) =>
                        setEventForm((f) => ({
                          ...f,
                          occurred_at: e.target.value,
                        }))
                      }
                      className="input w-full"
                    />
                  </div>
                  <div className="md:col-span-3">
                    <label className="block text-xs font-medium text-neutral-700 mb-1">
                      Description (optionnel)
                    </label>
                    <textarea
                      value={eventForm.body}
                      onChange={(e) =>
                        setEventForm((f) => ({
                          ...f,
                          body: e.target.value,
                        }))
                      }
                      placeholder="Détails de l\u2019événement..."
                      className="input w-full"
                      rows={2}
                    />
                  </div>
                </div>
                <div className="flex justify-end mt-4">
                  <button
                    onClick={submitEvent}
                    disabled={eventSubmitting || !eventForm.title.trim()}
                    className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {eventSubmitting && (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    )}
                    Enregistrer
                  </button>
                </div>
              </div>
            )}

            {tabLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-accent" />
              </div>
            ) : timeline.length === 0 && !showEventForm ? (
              <div className="card text-center py-12">
                <CalendarClock className="w-12 h-12 mx-auto mb-4 text-neutral-300" />
                <p className="text-neutral-500 font-medium">
                  Aucun événement dans la chronologie
                </p>
                <p className="text-neutral-400 text-sm mt-1">
                  Ajoutez un événement pour constituer l&apos;historique de ce
                  dossier.
                </p>
              </div>
            ) : (
              timeline.length > 0 && (
                <div className="relative pl-6">
                  {/* vertical line */}
                  <div className="absolute left-[11px] top-2 bottom-2 w-0.5 bg-neutral-200" />

                  <div className="space-y-6">
                    {timeline.map((ev) => {
                      const dotColor =
                        SOURCE_COLORS[ev.source] ?? "bg-neutral-400";
                      return (
                        <div key={ev.id} className="relative flex gap-4">
                          {/* dot */}
                          <div
                            className={`absolute -left-6 top-1.5 w-3.5 h-3.5 rounded-full border-2 border-white ${dotColor} z-10 shadow-subtle`}
                          />

                          {/* card */}
                          <div className="card flex-1">
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex items-center gap-2 flex-wrap">
                                <h3 className="text-sm font-semibold text-neutral-900">
                                  {ev.title}
                                </h3>
                                <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-neutral-100 text-neutral-600">
                                  {eventTypeLabel(ev.event_type)}
                                </span>
                                <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-neutral-50 text-neutral-500">
                                  {ev.source}
                                </span>
                              </div>
                              <span className="text-xs text-neutral-500 flex-shrink-0 ml-4">
                                {fmtDateLong(ev.occurred_at)}
                              </span>
                            </div>

                            {ev.body && (
                              <p className="text-sm text-neutral-700 whitespace-pre-wrap mb-2">
                                {ev.body}
                              </p>
                            )}

                            {ev.evidence_links.length > 0 && (
                              <div className="flex flex-wrap gap-2 mt-2">
                                {ev.evidence_links.map((link, li) => {
                                  const FIcon = fileIcon(link.mime_type);
                                  return (
                                    <span
                                      key={li}
                                      className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-neutral-50 border border-neutral-200 text-xs text-neutral-600"
                                    >
                                      <FIcon className="w-3.5 h-3.5 text-accent" />
                                      {link.file_name}
                                      <span className="text-neutral-400">
                                        ({fmtFileSize(link.file_size_bytes)})
                                      </span>
                                    </span>
                                  );
                                })}
                              </div>
                            )}

                            {ev.created_by && (
                              <p className="text-xs text-neutral-400 mt-2">
                                Par {ev.created_by}
                              </p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ================================================================== */
/*  InlineField — click-to-edit field                                  */
/* ================================================================== */

function InlineField({
  label,
  value,
  placeholder,
  readOnly,
  editing,
  editValue,
  saving,
  inputType = "text",
  multiline,
  onStartEdit,
  onChangeEdit,
  onCommit,
  onCancel,
}: {
  label: string;
  value: string;
  placeholder?: string;
  readOnly?: boolean;
  editing?: boolean;
  editValue?: string;
  saving?: boolean;
  inputType?: string;
  multiline?: boolean;
  onStartEdit?: () => void;
  onChangeEdit?: (v: string) => void;
  onCommit?: () => void;
  onCancel?: () => void;
}) {
  if (readOnly) {
    return (
      <div>
        <p className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">
          {label}
        </p>
        <p className="text-sm text-neutral-900">{value || placeholder || "\u2014"}</p>
      </div>
    );
  }

  if (editing) {
    return (
      <div>
        <p className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">
          {label}
        </p>
        {multiline ? (
          <textarea
            value={editValue ?? ""}
            onChange={(e) => onChangeEdit?.(e.target.value)}
            onBlur={() => onCommit?.()}
            onKeyDown={(e) => {
              if (e.key === "Escape") onCancel?.();
            }}
            className="input w-full text-sm"
            rows={3}
            autoFocus
            disabled={saving}
          />
        ) : (
          <input
            type={inputType}
            value={editValue ?? ""}
            onChange={(e) => onChangeEdit?.(e.target.value)}
            onBlur={() => onCommit?.()}
            onKeyDown={(e) => {
              if (e.key === "Enter") onCommit?.();
              if (e.key === "Escape") onCancel?.();
            }}
            className="input w-full text-sm"
            autoFocus
            disabled={saving}
          />
        )}
      </div>
    );
  }

  return (
    <div>
      <button
        onClick={() => onStartEdit?.()}
        className="text-left w-full group"
        type="button"
      >
        <p className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1 group-hover:text-accent transition-colors">
          {label}
        </p>
        <p className="text-sm text-neutral-900">
          {value || (
            <span className="text-neutral-400 italic">
              {placeholder || "\u2014"}
            </span>
          )}
        </p>
      </button>
    </div>
  );
}

/* ================================================================== */
/*  InlineFieldSelect — click-to-edit dropdown                         */
/* ================================================================== */

function InlineFieldSelect({
  label,
  value,
  editing,
  editValue,
  saving,
  options,
  onStartEdit,
  onChangeEdit,
  onCommit,
  onCancel,
}: {
  label: string;
  value: string;
  editing?: boolean;
  editValue?: string;
  saving?: boolean;
  options: { value: string; label: string }[];
  onStartEdit?: () => void;
  onChangeEdit?: (v: string) => void;
  onCommit?: () => void;
  onCancel?: () => void;
}) {
  if (editing) {
    return (
      <div>
        <p className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">
          {label}
        </p>
        <select
          value={editValue ?? ""}
          onChange={(e) => {
            onChangeEdit?.(e.target.value);
            // commit immediately on select
            setTimeout(() => onCommit?.(), 0);
          }}
          onBlur={() => onCommit?.()}
          onKeyDown={(e) => {
            if (e.key === "Escape") onCancel?.();
          }}
          className="input w-full text-sm"
          autoFocus
          disabled={saving}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <div>
      <button
        onClick={() => onStartEdit?.()}
        className="text-left w-full group"
        type="button"
      >
        <p className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1 group-hover:text-accent transition-colors">
          {label}
        </p>
        <p className="text-sm text-neutral-900">{value}</p>
      </button>
    </div>
  );
}
