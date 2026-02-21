"use client";

import { useAuth } from "@/lib/useAuth";
import { useEffect, useState, useCallback, useRef } from "react";
import {
  Inbox,
  Mail,
  Phone,
  FileText,
  Loader2,
  Check,
  ChevronDown,
  ChevronUp,
  FolderPlus,
  CheckCircle2,
  XCircle,
  Clock,
  Sparkles,
  ArrowRight,
  Calendar,
  Link2,
  Zap,
  Brain,
  AlertTriangle,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, EmptyState, Badge, Modal, Card, Tabs, Button } from "@/components/ui";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface RawPayload {
  title?: string;
  subject?: string;
  from?: string;
  body?: string;
}

interface InboxItem {
  id: string;
  source: string;
  status: string;
  raw_payload: RawPayload;
  suggested_case_id: string | null;
  confidence: number;
  created_at: string;
}

interface InboxListResponse {
  items: InboxItem[];
  total: number;
}

interface CaseOption {
  id: string;
  reference: string;
  title: string;
}

interface CaseListResponse {
  items: CaseOption[];
  total: number;
}

/* --- AI Triage Types --- */

interface AIClassification {
  category: "URGENT" | "ACTION_REQUIRED" | "NORMAL" | "INFO_ONLY" | "DELEGABLE" | "SPAM";
  confidence: number;
  reasons: string[];
  suggested_priority: number;
}

interface AIDeadline {
  date: string;
  description: string;
  days_remaining: number;
}

interface AISuggestion {
  case_id?: string;
  case_reference?: string;
  case_title?: string;
  relevance: number;
}

interface AITriageResult {
  classification: AIClassification;
  suggestions?: AISuggestion[];
  deadlines?: AIDeadline[];
}

type AIFilterCategory = "" | "URGENT" | "ACTION_REQUIRED" | "INFO_ONLY" | "DELEGABLE";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const STATUS_FILTERS = [
  { label: "Tous", value: "" },
  { label: "En attente", value: "DRAFT" },
  { label: "Validés", value: "VALIDATED" },
  { label: "Refusés", value: "REFUSED" },
];

const EVENT_TYPES = [
  { value: "email_received", label: "E-mail reçu" },
  { value: "email_sent", label: "E-mail envoyé" },
  { value: "call_inbound", label: "Appel entrant" },
  { value: "call_outbound", label: "Appel sortant" },
  { value: "document_received", label: "Document reçu" },
  { value: "document_sent", label: "Document envoyé" },
  { value: "note", label: "Note interne" },
  { value: "meeting", label: "Réunion" },
  { value: "hearing", label: "Audience" },
  { value: "other", label: "Autre" },
];

const MATTER_TYPES = [
  { value: "general", label: "Général" },
  { value: "civil", label: "Civil" },
  { value: "penal", label: "Pénal" },
  { value: "commercial", label: "Commercial" },
  { value: "social", label: "Social" },
  { value: "fiscal", label: "Fiscal" },
  { value: "family", label: "Familial" },
  { value: "administrative", label: "Administratif" },
];

const statusStyles: Record<string, string> = {
  DRAFT: "bg-warning-50 text-warning-700",
  VALIDATED: "bg-success-50 text-success-700",
  REFUSED: "bg-danger-50 text-danger-700",
};

const statusLabels: Record<string, string> = {
  DRAFT: "En attente",
  VALIDATED: "Validé",
  REFUSED: "Refusé",
};

const AI_CATEGORY_LABELS: Record<string, string> = {
  URGENT: "Urgent",
  ACTION_REQUIRED: "Action requise",
  NORMAL: "Normal",
  INFO_ONLY: "Informatif",
  DELEGABLE: "Delegable",
  SPAM: "Spam",
};

const AI_CATEGORY_DESCRIPTIONS: Record<string, string> = {
  URGENT: "Delai tribunal ou action immediate requise",
  ACTION_REQUIRED: "Necessite une action de l'avocat",
  NORMAL: "Traitement standard",
  INFO_ONLY: "Pour information uniquement",
  DELEGABLE: "Peut etre delegue a un assistant",
  SPAM: "Non pertinent ou publicite",
};

const AI_FILTER_BUTTONS: { label: string; value: AIFilterCategory; colorClass: string; badgeVariant: "danger" | "warning" | "accent" | "default" }[] = [
  { label: "Tous", value: "", colorClass: "bg-neutral-100 text-neutral-700 hover:bg-neutral-200", badgeVariant: "default" },
  { label: "Urgents", value: "URGENT", colorClass: "bg-danger-50 text-danger-700 hover:bg-danger-100", badgeVariant: "danger" },
  { label: "Action requise", value: "ACTION_REQUIRED", colorClass: "bg-warning-50 text-warning-700 hover:bg-warning-100", badgeVariant: "warning" },
  { label: "Informatif", value: "INFO_ONLY", colorClass: "bg-accent-50 text-accent-700 hover:bg-accent-100", badgeVariant: "accent" },
  { label: "Delegable", value: "DELEGABLE", colorClass: "bg-neutral-50 text-neutral-600 hover:bg-neutral-100", badgeVariant: "default" },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function sourceIcon(source: string) {
  switch (source.toLowerCase()) {
    case "outlook":
    case "email":
      return <Mail className="w-5 h-5" />;
    case "ringover":
    case "phone":
      return <Phone className="w-5 h-5" />;
    case "dpa":
    case "document":
      return <FileText className="w-5 h-5" />;
    default:
      return <Inbox className="w-5 h-5" />;
  }
}

function sourceColor(source: string): string {
  switch (source.toLowerCase()) {
    case "outlook":
    case "email":
      return "bg-accent-50 text-accent";
    case "ringover":
    case "phone":
      return "bg-success-50 text-success";
    case "dpa":
    case "document":
      return "bg-warning-50 text-warning";
    default:
      return "bg-neutral-100 text-neutral-500";
  }
}

function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "A l'instant";
  if (diffMin < 60) return `Il y a ${diffMin} min`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `Il y a ${diffH}h`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 7) return `Il y a ${diffD}j`;
  return date.toLocaleDateString("fr-BE", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function itemTitle(item: InboxItem): string {
  return (
    item.raw_payload.title ||
    item.raw_payload.subject ||
    `Element ${item.source}`
  );
}

function generateReference(): string {
  const year = new Date().getFullYear();
  const num = String(Math.floor(Math.random() * 999) + 1).padStart(3, "0");
  return `DOS-${year}-${num}`;
}

/* --- AI Helpers --- */

function aiCategoryBorderColor(category: string): string {
  switch (category) {
    case "URGENT":
      return "border-l-4 border-l-danger";
    case "ACTION_REQUIRED":
      return "border-l-4 border-l-warning";
    case "INFO_ONLY":
      return "border-l-4 border-l-accent";
    case "DELEGABLE":
      return "border-l-4 border-l-neutral-400";
    case "SPAM":
      return "border-l-4 border-l-neutral-300";
    default:
      return "border-l-4 border-l-success";
  }
}

function aiCategoryBadgeVariant(category: string): "danger" | "warning" | "accent" | "neutral" | "success" | "default" {
  switch (category) {
    case "URGENT":
      return "danger";
    case "ACTION_REQUIRED":
      return "warning";
    case "INFO_ONLY":
      return "accent";
    case "DELEGABLE":
      return "neutral";
    case "SPAM":
      return "neutral";
    default:
      return "success";
  }
}

function aiCategoryShortLabel(category: string, reasons: string[]): string {
  switch (category) {
    case "URGENT":
      if (reasons.some((r) => r.toLowerCase().includes("delai"))) return "Urgent: delai procedure";
      if (reasons.some((r) => r.toLowerCase().includes("tribunal"))) return "Urgent: delai tribunal";
      return "Urgent: action immediate";
    case "ACTION_REQUIRED":
      return "Action: reponse requise";
    case "INFO_ONLY":
      if (reasons.some((r) => r.toLowerCase().includes("newsletter") || r.toLowerCase().includes("informatif"))) return "Info: newsletter";
      return "Info: pour information";
    case "DELEGABLE":
      return "Delegable: assistant";
    case "SPAM":
      return "Spam: non pertinent";
    default:
      return "Normal: traitement standard";
  }
}

function deadlineBadgeColor(daysRemaining: number): string {
  if (daysRemaining <= 3) return "bg-danger-100 text-danger-700";
  if (daysRemaining <= 7) return "bg-warning-100 text-warning-700";
  return "bg-accent-100 text-accent-700";
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function InboxPage() {
  const { accessToken, tenantId, userId } = useAuth();

  /* --- State --- */
  const [items, setItems] = useState<InboxItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [cases, setCases] = useState<CaseOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  /* Validate modal */
  const [validateTarget, setValidateTarget] = useState<InboxItem | null>(null);
  const [validateForm, setValidateForm] = useState({
    case_id: "",
    event_type: "email_received",
    title: "",
    body: "",
  });

  /* Refuse confirm */
  const [refuseTarget, setRefuseTarget] = useState<InboxItem | null>(null);

  /* Create case modal */
  const [createCaseTarget, setCreateCaseTarget] = useState<InboxItem | null>(
    null,
  );
  const [createCaseForm, setCreateCaseForm] = useState({
    reference: generateReference(),
    title: "",
    matter_type: "general",
  });

  /* --- AI Triage State --- */
  const [aiTriageMap, setAiTriageMap] = useState<Record<string, AITriageResult>>({});
  const [aiFilter, setAiFilter] = useState<AIFilterCategory>("");
  const [expandedItemId, setExpandedItemId] = useState<string | null>(null);
  const [bulkTriageRunning, setBulkTriageRunning] = useState(false);
  const [bulkTriageProgress, setBulkTriageProgress] = useState({ current: 0, total: 0 });
  const [linkingCaseItemId, setLinkingCaseItemId] = useState<string | null>(null);
  const bulkTriageCancelledRef = useRef(false);

  /* --- Data loading --- */
  const loadItems = useCallback(() => {
    if (!accessToken) return;
    setLoading(true);
    setError(null);

    const statusParam = statusFilter ? `?status=${statusFilter}` : "";
    apiFetch<InboxListResponse>(`/inbox${statusParam}`, accessToken, { tenantId })
      .then((data) => {
        setItems(data.items);
        setTotalCount(data.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [accessToken, tenantId, statusFilter]);

  const loadCases = useCallback(() => {
    if (!accessToken) return;
    apiFetch<CaseListResponse>("/cases", accessToken, { tenantId })
      .then((data) => setCases(data.items))
      .catch(() => {});
  }, [accessToken, tenantId]);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  /* --- AI Triage: classify a single item --- */
  const classifyItem = useCallback(
    async (item: InboxItem): Promise<AITriageResult | null> => {
      const subject = item.raw_payload.subject || item.raw_payload.title || "";
      const body = item.raw_payload.body || "";
      const sender = item.raw_payload.from || "";

      if (!accessToken) {
        return null;
      }

      try {
        /* Try the full ML pipeline first */
        const result = await apiFetch<{
          classification: AIClassification;
          suggestions?: AISuggestion[];
          deadlines?: AIDeadline[];
        }>("/ml/process", accessToken, {
          tenantId,
          method: "POST",
          body: JSON.stringify({
            subject,
            body,
            sender,
            type: item.source,
            existing_cases: cases.map((c) => ({ id: c.id, reference: c.reference, title: c.title })),
          }),
        });
        return {
          classification: result.classification,
          suggestions: result.suggestions || [],
          deadlines: result.deadlines || [],
        };
      } catch {
        /* Fallback: try simpler classify endpoint */
        try {
          const classifyResult = await apiFetch<AIClassification>("/ml/classify", accessToken, {
            tenantId,
            method: "POST",
            body: JSON.stringify({ subject, body, sender }),
          });
          return { classification: classifyResult, deadlines: [], suggestions: [] };
        } catch {
          /* Classification unavailable */
          return null;
        }
      }
    },
    [accessToken, tenantId, cases],
  );

  /* --- AI Triage: bulk classify all unclassified items --- */
  const handleBulkTriage = useCallback(async () => {
    const unclassified = items.filter((item) => !aiTriageMap[item.id]);
    if (unclassified.length === 0) {
      setSuccess("Tous les elements sont deja classifies par l'IA.");
      setTimeout(() => setSuccess(null), 3000);
      return;
    }

    setBulkTriageRunning(true);
    setBulkTriageProgress({ current: 0, total: unclassified.length });
    bulkTriageCancelledRef.current = false;

    const newMap = { ...aiTriageMap };

    for (let i = 0; i < unclassified.length; i++) {
      if (bulkTriageCancelledRef.current) break;

      const item = unclassified[i];
      try {
        const result = await classifyItem(item);
        if (result) {
          newMap[item.id] = result;
          setAiTriageMap({ ...newMap });
        }
      } catch {
        /* Skip failed items silently */
      }
      setBulkTriageProgress({ current: i + 1, total: unclassified.length });
    }

    setBulkTriageRunning(false);
    if (!bulkTriageCancelledRef.current) {
      setSuccess(`${unclassified.length} elements analyses par l'IA.`);
      setTimeout(() => setSuccess(null), 3000);
    }
  }, [items, aiTriageMap, classifyItem]);

  /* --- AI Triage: classify single item on expand --- */
  const [aiUnavailableItems, setAiUnavailableItems] = useState<Set<string>>(new Set());
  const handleExpandItem = useCallback(
    async (itemId: string) => {
      if (expandedItemId === itemId) {
        setExpandedItemId(null);
        return;
      }
      setExpandedItemId(itemId);

      /* Auto-classify if not already done */
      if (!aiTriageMap[itemId] && !aiUnavailableItems.has(itemId)) {
        const item = items.find((i) => i.id === itemId);
        if (item) {
          try {
            const result = await classifyItem(item);
            if (result) {
              setAiTriageMap((prev) => ({ ...prev, [itemId]: result }));
            } else {
              setAiUnavailableItems((prev) => new Set(prev).add(itemId));
            }
          } catch {
            setAiUnavailableItems((prev) => new Set(prev).add(itemId));
          }
        }
      }
    },
    [expandedItemId, aiTriageMap, aiUnavailableItems, items, classifyItem],
  );

  /* --- AI Triage: link to suggested case --- */
  const handleLinkToCase = useCallback(
    async (itemId: string, caseId: string) => {
      if (!accessToken) return;
      setLinkingCaseItemId(itemId);
      try {
        await apiFetch(`/inbox/${itemId}`, accessToken, {
          tenantId,
          method: "PATCH",
          body: JSON.stringify({ suggested_case_id: caseId }),
        });
        setSuccess("Element lie au dossier suggere.");
        loadItems();
        setTimeout(() => setSuccess(null), 3000);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Une erreur est survenue";
        setError(message);
      } finally {
        setLinkingCaseItemId(null);
      }
    },
    [accessToken, tenantId, loadItems],
  );

  /* --- Actions --- */
  const handleValidate = async () => {
    if (!accessToken || !validateTarget || !validateForm.case_id || !validateForm.title.trim())
      return;
    setActionLoading(validateTarget.id);
    setError(null);
    try {
      await apiFetch(`/inbox/${validateTarget.id}/validate`, accessToken, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          case_id: validateForm.case_id,
          event_type: validateForm.event_type,
          title: validateForm.title,
          body: validateForm.body || undefined,
        }),
      });
      setSuccess("Element valide et ajoute au dossier.");
      setValidateTarget(null);
      setValidateForm({
        case_id: "",
        event_type: "email_received",
        title: "",
        body: "",
      });
      loadItems();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Une erreur est survenue";
      setError(message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRefuse = async () => {
    if (!accessToken || !refuseTarget) return;
    setActionLoading(refuseTarget.id);
    setError(null);
    try {
      await apiFetch(`/inbox/${refuseTarget.id}/refuse`, accessToken, {
        tenantId,
        method: "POST",
      });
      setSuccess("Element refuse.");
      setRefuseTarget(null);
      loadItems();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Une erreur est survenue";
      setError(message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleCreateCase = async () => {
    if (
      !accessToken ||
      !createCaseTarget ||
      !createCaseForm.title.trim() ||
      !createCaseForm.reference.trim()
    )
      return;
    setActionLoading(createCaseTarget.id);
    setError(null);
    try {
      await apiFetch(`/inbox/${createCaseTarget.id}/create-case`, accessToken, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          reference: createCaseForm.reference,
          title: createCaseForm.title,
          matter_type: createCaseForm.matter_type,
          responsible_user_id: userId,
        }),
      });
      setSuccess("Nouveau dossier cree a partir de cet element.");
      setCreateCaseTarget(null);
      setCreateCaseForm({
        reference: generateReference(),
        title: "",
        matter_type: "general",
      });
      loadItems();
      loadCases();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Une erreur est survenue";
      setError(message);
    } finally {
      setActionLoading(null);
    }
  };

  /* Open validate modal with pre-filled data */
  const openValidate = (item: InboxItem) => {
    const triage = aiTriageMap[item.id];
    const suggestedCaseId =
      item.suggested_case_id ||
      (triage?.suggestions && triage.suggestions.length > 0
        ? triage.suggestions[0].case_id
        : "") ||
      "";
    setValidateForm({
      case_id: suggestedCaseId,
      event_type: "email_received",
      title: itemTitle(item),
      body: item.raw_payload.body || "",
    });
    setValidateTarget(item);
  };

  /* Open create case modal with pre-filled data */
  const openCreateCase = (item: InboxItem) => {
    setCreateCaseForm({
      reference: generateReference(),
      title: itemTitle(item),
      matter_type: "general",
    });
    setCreateCaseTarget(item);
  };

  /* --- Filtered items (status + AI category) --- */
  const filteredItems = items.filter((item) => {
    /* AI category filter */
    if (aiFilter) {
      const triage = aiTriageMap[item.id];
      if (!triage) return false;
      return triage.classification.category === aiFilter;
    }
    return true;
  });

  /* --- AI filter counts --- */
  const aiFilterCounts: Record<string, number> = {
    "": items.length,
    URGENT: 0,
    ACTION_REQUIRED: 0,
    INFO_ONLY: 0,
    DELEGABLE: 0,
  };
  for (const item of items) {
    const triage = aiTriageMap[item.id];
    if (triage) {
      const cat = triage.classification.category;
      if (cat in aiFilterCounts) {
        aiFilterCounts[cat]++;
      }
    }
  }

  const hasAnyTriage = Object.keys(aiTriageMap).length > 0;

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  if (loading) {
    return <LoadingSkeleton variant="list" />;
  }

  return (
    <div>
      {/* Success toast */}
      {success && (
        <div className="fixed top-4 right-4 z-50 bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-md text-sm flex items-center gap-2 shadow-lg animate-in fade-in">
          <Check className="w-4 h-4" />
          {success}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-neutral-900">Inbox</h1>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-accent-50 text-accent-700">
            {totalCount}
          </span>
        </div>
        {/* Bulk AI Triage Button */}
        <div className="flex items-center gap-3">
          {bulkTriageRunning && (
            <div className="flex items-center gap-2 text-sm text-neutral-600">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>
                Analyse {bulkTriageProgress.current}/{bulkTriageProgress.total}
              </span>
              <div className="w-24 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent rounded-full transition-all duration-300"
                  style={{
                    width: bulkTriageProgress.total > 0
                      ? `${Math.round((bulkTriageProgress.current / bulkTriageProgress.total) * 100)}%`
                      : "0%",
                  }}
                />
              </div>
              <button
                onClick={() => { bulkTriageCancelledRef.current = true; }}
                className="text-xs text-neutral-400 hover:text-danger transition-colors"
              >
                Annuler
              </button>
            </div>
          )}
          <Button
            size="sm"
            variant="secondary"
            icon={<Zap className="w-3.5 h-3.5" />}
            onClick={handleBulkTriage}
            disabled={bulkTriageRunning || items.length === 0}
            loading={bulkTriageRunning}
          >
            Trier avec IA
          </Button>
        </div>
      </div>

      {/* Filter tabs with pills and badge counts */}
      <div className="mb-4">
        <Tabs
          tabs={STATUS_FILTERS.map((f) => ({
            id: f.value,
            label: f.label,
            content: null,
            badge:
              f.value === ""
                ? totalCount
                : f.value === "DRAFT"
                  ? items.filter((i) => i.status === "DRAFT").length
                  : f.value === "VALIDATED"
                    ? items.filter((i) => i.status === "VALIDATED").length
                    : items.filter((i) => i.status === "REFUSED").length,
          }))}
          defaultTab={statusFilter || ""}
          onTabChange={setStatusFilter}
        />
      </div>

      {/* AI Smart Filter Bar */}
      {hasAnyTriage && (
        <div className="mb-6">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1.5 text-xs text-neutral-500 mr-1">
              <Brain className="w-3.5 h-3.5" />
              <span className="font-medium">Filtre IA :</span>
            </div>
            {AI_FILTER_BUTTONS.map((btn) => {
              const isActive = aiFilter === btn.value;
              const count = aiFilterCounts[btn.value] || 0;
              return (
                <button
                  key={btn.value || "all"}
                  onClick={() => setAiFilter(btn.value)}
                  className={`
                    inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium
                    transition-all duration-150
                    ${isActive
                      ? `${btn.colorClass} ring-2 ring-offset-1 ring-neutral-300 shadow-sm`
                      : "bg-white text-neutral-500 border border-neutral-200 hover:border-neutral-300 hover:text-neutral-700"
                    }
                  `}
                >
                  {btn.label}
                  {count > 0 && (
                    <span
                      className={`
                        inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px]
                        font-bold rounded-full
                        ${isActive
                          ? btn.value === "URGENT"
                            ? "bg-danger-200 text-danger-800"
                            : btn.value === "ACTION_REQUIRED"
                              ? "bg-warning-200 text-warning-800"
                              : btn.value === "INFO_ONLY"
                                ? "bg-accent-200 text-accent-800"
                                : "bg-neutral-200 text-neutral-700"
                          : "bg-neutral-100 text-neutral-500"
                        }
                      `}
                    >
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
            {aiFilter && (
              <button
                onClick={() => setAiFilter("")}
                className="text-xs text-neutral-400 hover:text-neutral-600 underline ml-1 transition-colors"
              >
                Effacer le filtre
              </button>
            )}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-4">
          <ErrorState message={error} onRetry={() => setError(null)} />
        </div>
      )}

      {/* ---- Validate Modal ---- */}
      <Modal
        isOpen={!!validateTarget}
        onClose={() => setValidateTarget(null)}
        title="Valider et rattacher a un dossier"
        footer={
          <div className="flex justify-end gap-3">
            <button
              onClick={() => setValidateTarget(null)}
              className="btn-secondary"
            >
              Annuler
            </button>
            <button
              onClick={handleValidate}
              disabled={
                validateTarget && actionLoading === validateTarget.id ||
                !validateForm.case_id ||
                !validateForm.title.trim()
              }
              className="btn-primary flex items-center gap-2 disabled:opacity-50"
            >
              {validateTarget && actionLoading === validateTarget.id && (
                <Loader2 className="w-4 h-4 animate-spin" />
              )}
              <CheckCircle2 className="w-4 h-4" />
              Valider
            </button>
          </div>
        }
      >
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Dossier
                </label>
                <div className="relative">
                  <select
                    value={validateForm.case_id}
                    onChange={(e) =>
                      setValidateForm((f) => ({
                        ...f,
                        case_id: e.target.value,
                      }))
                    }
                    className="input appearance-none pr-8"
                  >
                    <option value="">-- Selectionner un dossier --</option>
                    {cases.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.reference} -- {c.title}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 pointer-events-none" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Type d&apos;evenement
                </label>
                <div className="relative">
                  <select
                    value={validateForm.event_type}
                    onChange={(e) =>
                      setValidateForm((f) => ({
                        ...f,
                        event_type: e.target.value,
                      }))
                    }
                    className="input appearance-none pr-8"
                  >
                    {EVENT_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 pointer-events-none" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Titre
                </label>
                <input
                  type="text"
                  value={validateForm.title}
                  onChange={(e) =>
                    setValidateForm((f) => ({ ...f, title: e.target.value }))
                  }
                  placeholder="Titre de l'evenement"
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Corps (optionnel)
                </label>
                <textarea
                  value={validateForm.body}
                  onChange={(e) =>
                    setValidateForm((f) => ({ ...f, body: e.target.value }))
                  }
                  placeholder="Details supplementaires..."
                  className="input"
                  rows={3}
                />
              </div>
            </div>
      </Modal>

      {/* ---- Refuse Confirm ---- */}
      <Modal
        isOpen={!!refuseTarget}
        onClose={() => setRefuseTarget(null)}
        title="Confirmer le refus"
        size="sm"
        footer={
          <div className="flex justify-end gap-3">
            <button
              onClick={() => setRefuseTarget(null)}
              className="btn-secondary"
            >
              Annuler
            </button>
            <button
              onClick={handleRefuse}
              disabled={!!(refuseTarget && actionLoading === refuseTarget.id)}
              className="px-4 py-2 text-sm font-medium text-white bg-danger rounded-md hover:bg-danger/90 transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              {refuseTarget && actionLoading === refuseTarget.id && (
                <Loader2 className="w-4 h-4 animate-spin" />
              )}
              <XCircle className="w-4 h-4" />
              Refuser
            </button>
          </div>
        }
      >
            <p className="text-sm text-neutral-600 mb-6">
              Etes-vous sur de vouloir refuser cet element ? Cette action
              marquera l&apos;entree comme non pertinente.
            </p>
            {refuseTarget && (
              <div className="bg-neutral-50 rounded-md p-3 mb-6">
                <p className="text-sm font-medium text-neutral-800">
                  {itemTitle(refuseTarget)}
                </p>
                {refuseTarget.raw_payload.from && (
                  <p className="text-xs text-neutral-500 mt-1">
                    De : {refuseTarget.raw_payload.from}
                  </p>
                )}
              </div>
            )}
      </Modal>

      {/* ---- Create Case Modal ---- */}
      <Modal
        isOpen={!!createCaseTarget}
        onClose={() => setCreateCaseTarget(null)}
        title="Creer un nouveau dossier"
        footer={
          <div className="flex justify-end gap-3">
            <button
              onClick={() => setCreateCaseTarget(null)}
              className="btn-secondary"
            >
              Annuler
            </button>
            <button
              onClick={handleCreateCase}
              disabled={
                createCaseTarget && actionLoading === createCaseTarget.id ||
                !createCaseForm.title.trim() ||
                !createCaseForm.reference.trim()
              }
              className="btn-primary flex items-center gap-2 disabled:opacity-50"
            >
              {createCaseTarget && actionLoading === createCaseTarget.id && (
                <Loader2 className="w-4 h-4 animate-spin" />
              )}
              <FolderPlus className="w-4 h-4" />
              Creer le dossier
            </button>
          </div>
        }
      >
            <div className="bg-accent-50/50 border border-accent-100 rounded-md p-3 mb-5">
              <p className="text-xs text-accent-600">
                Un dossier sera cree et cet element y sera automatiquement
                rattache.
              </p>
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Reference
                  </label>
                  <input
                    type="text"
                    value={createCaseForm.reference}
                    onChange={(e) =>
                      setCreateCaseForm((f) => ({
                        ...f,
                        reference: e.target.value,
                      }))
                    }
                    className="input"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Type de matiere
                  </label>
                  <div className="relative">
                    <select
                      value={createCaseForm.matter_type}
                      onChange={(e) =>
                        setCreateCaseForm((f) => ({
                          ...f,
                          matter_type: e.target.value,
                        }))
                      }
                      className="input appearance-none pr-8"
                    >
                      {MATTER_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 pointer-events-none" />
                  </div>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Titre du dossier
                </label>
                <input
                  type="text"
                  value={createCaseForm.title}
                  onChange={(e) =>
                    setCreateCaseForm((f) => ({ ...f, title: e.target.value }))
                  }
                  placeholder="Ex : Dupont c/ SA Immobel"
                  className="input"
                />
              </div>
            </div>
      </Modal>

      {/* ---- Item list ---- */}
      {filteredItems.length === 0 ? (
        <Card className="text-center py-20">
          <EmptyState
            title="Aucun element"
            description={
              aiFilter
                ? `Aucun element classe comme "${AI_CATEGORY_LABELS[aiFilter] || aiFilter}". Lancez le tri IA ou essayez un autre filtre.`
                : statusFilter
                  ? "Aucun element ne correspond a ce filtre. Essayez un autre statut."
                  : "Votre inbox est vide. Les nouveaux e-mails, appels et documents apparaitront ici automatiquement."
            }
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredItems.map((item) => {
            const triage = aiTriageMap[item.id];
            const isExpanded = expandedItemId === item.id;
            const hasTriage = !!triage;

            return (
              <Card
                key={item.id}
                hover
                className={`border border-neutral-100 hover:border-accent-200 ${
                  hasTriage ? aiCategoryBorderColor(triage.classification.category) : ""
                } ${triage?.classification.category === "SPAM" ? "opacity-60" : ""}`}
              >
                <div className="flex items-start gap-4">
                  {/* Source icon */}
                  <div
                    className={`w-10 h-10 rounded flex items-center justify-center flex-shrink-0 ${sourceColor(item.source)}`}
                  >
                    {sourceIcon(item.source)}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <h3
                            className={`text-sm font-semibold text-neutral-900 truncate ${
                              triage?.classification.category === "SPAM" ? "line-through text-neutral-500" : ""
                            }`}
                          >
                            {itemTitle(item)}
                          </h3>
                          {/* AI Classification Tag */}
                          {hasTriage && (
                            <Badge
                              variant={aiCategoryBadgeVariant(triage.classification.category)}
                              size="sm"
                            >
                              {aiCategoryShortLabel(triage.classification.category, triage.classification.reasons)}
                            </Badge>
                          )}
                        </div>
                        {item.raw_payload.from && (
                          <p className="text-xs text-neutral-500 mt-0.5">
                            De : {item.raw_payload.from}
                          </p>
                        )}
                        {item.raw_payload.body && (
                          <p className="text-sm text-neutral-600 mt-1.5 line-clamp-2">
                            {item.raw_payload.body}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {/* AI Confidence badge */}
                        {hasTriage && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-neutral-100 text-neutral-600">
                            <Sparkles className="w-3 h-3" />
                            IA: {Math.round(triage.classification.confidence * 100)}%
                          </span>
                        )}
                        {/* Deadline badge */}
                        {hasTriage && triage.deadlines && triage.deadlines.length > 0 && (
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold ${
                              deadlineBadgeColor(triage.deadlines[0].days_remaining)
                            }`}
                          >
                            <Calendar className="w-3 h-3" />
                            {triage.deadlines[0].days_remaining}j
                          </span>
                        )}
                        <span className="text-xs text-neutral-400 whitespace-nowrap">
                          {timeAgo(item.created_at)}
                        </span>
                        <Badge
                          variant={
                            item.status === "DRAFT"
                              ? "warning"
                              : item.status === "VALIDATED"
                                ? "success"
                                : "danger"
                          }
                          size="sm"
                        >
                          {statusLabels[item.status] || item.status}
                        </Badge>
                      </div>
                    </div>

                    {/* Confidence bar */}
                    <div className="flex items-center gap-2 mt-3">
                      <span className="text-xs text-neutral-400">Confiance</span>
                      <div className="flex-1 max-w-[200px] h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${
                            item.confidence >= 0.8
                              ? "bg-success"
                              : item.confidence >= 0.5
                                ? "bg-warning"
                                : "bg-danger"
                          }`}
                          style={{ width: `${Math.round(item.confidence * 100)}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-neutral-600">
                        {Math.round(item.confidence * 100)}%
                      </span>
                      {item.suggested_case_id && (
                        <Badge variant="accent" size="sm" className="ml-2">
                          Dossier suggere
                        </Badge>
                      )}
                    </div>

                    {/* Actions for DRAFT items */}
                    {item.status === "DRAFT" && (
                      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-neutral-100">
                        <Button
                          size="sm"
                          variant="primary"
                          icon={<CheckCircle2 className="w-3.5 h-3.5" />}
                          onClick={() => openValidate(item)}
                          disabled={actionLoading === item.id}
                        >
                          Valider
                        </Button>
                        <Button
                          size="sm"
                          variant="danger"
                          icon={<XCircle className="w-3.5 h-3.5" />}
                          onClick={() => setRefuseTarget(item)}
                          disabled={actionLoading === item.id}
                        >
                          Refuser
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          icon={<FolderPlus className="w-3.5 h-3.5" />}
                          onClick={() => openCreateCase(item)}
                          disabled={actionLoading === item.id}
                        >
                          Creer dossier
                        </Button>
                        {/* Expand/Collapse for AI Analysis */}
                        <Button
                          size="sm"
                          variant="ghost"
                          icon={<Sparkles className="w-3.5 h-3.5" />}
                          onClick={() => handleExpandItem(item.id)}
                        >
                          {isExpanded ? "Masquer IA" : "Analyse IA"}
                          {isExpanded ? (
                            <ChevronUp className="w-3 h-3 ml-0.5" />
                          ) : (
                            <ChevronDown className="w-3 h-3 ml-0.5" />
                          )}
                        </Button>
                        {actionLoading === item.id && (
                          <Loader2 className="w-4 h-4 animate-spin text-accent ml-1" />
                        )}
                      </div>
                    )}

                    {/* Status indicator for processed items */}
                    {item.status === "VALIDATED" && (
                      <div className="flex items-center justify-between mt-3 pt-3 border-t border-neutral-100">
                        <div className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-4 h-4 text-success" />
                          <span className="text-xs text-success-700">
                            Valide et rattache a un dossier
                          </span>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          icon={<Sparkles className="w-3.5 h-3.5" />}
                          onClick={() => handleExpandItem(item.id)}
                        >
                          {isExpanded ? "Masquer IA" : "Analyse IA"}
                        </Button>
                      </div>
                    )}
                    {item.status === "REFUSED" && (
                      <div className="flex items-center justify-between mt-3 pt-3 border-t border-neutral-100">
                        <div className="flex items-center gap-1.5">
                          <XCircle className="w-4 h-4 text-danger" />
                          <span className="text-xs text-danger-700">
                            Refuse -- non rattache
                          </span>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          icon={<Sparkles className="w-3.5 h-3.5" />}
                          onClick={() => handleExpandItem(item.id)}
                        >
                          {isExpanded ? "Masquer IA" : "Analyse IA"}
                        </Button>
                      </div>
                    )}

                    {/* ---- AI Analysis Panel (expanded) ---- */}
                    {isExpanded && (
                      <div className="mt-4 pt-4 border-t border-neutral-100">
                        <div className="bg-neutral-50 rounded-lg p-4">
                          <div className="flex items-center gap-2 mb-3">
                            <Brain className="w-4 h-4 text-accent" />
                            <h4 className="text-sm font-semibold text-neutral-800">
                              Analyse IA
                            </h4>
                          </div>

                          {!hasTriage && aiUnavailableItems.has(item.id) ? (
                            <div className="flex items-center gap-2 text-sm text-neutral-500">
                              <AlertTriangle className="w-4 h-4 text-warning" />
                              <span>Classification IA indisponible</span>
                            </div>
                          ) : !hasTriage ? (
                            <div className="flex items-center gap-2 text-sm text-neutral-500">
                              <Loader2 className="w-4 h-4 animate-spin" />
                              <span>Analyse en cours...</span>
                            </div>
                          ) : (
                            <div className="space-y-4">
                              {/* Classification */}
                              <div>
                                <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-1.5">
                                  Classification
                                </p>
                                <div className="flex items-center gap-2">
                                  <Badge
                                    variant={aiCategoryBadgeVariant(triage.classification.category)}
                                    size="md"
                                    dot
                                  >
                                    {AI_CATEGORY_LABELS[triage.classification.category] || triage.classification.category}
                                  </Badge>
                                  <span className="text-xs text-neutral-500">
                                    Confiance : {Math.round(triage.classification.confidence * 100)}%
                                  </span>
                                  <span className="text-xs text-neutral-400">
                                    | Priorite : {triage.classification.suggested_priority}/5
                                  </span>
                                </div>
                                <p className="text-xs text-neutral-500 mt-1">
                                  {AI_CATEGORY_DESCRIPTIONS[triage.classification.category] || ""}
                                </p>
                              </div>

                              {/* Reasons */}
                              <div>
                                <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-1.5">
                                  Raisons de la classification
                                </p>
                                <ul className="space-y-1">
                                  {triage.classification.reasons.map((reason, idx) => (
                                    <li
                                      key={idx}
                                      className="flex items-start gap-1.5 text-xs text-neutral-600"
                                    >
                                      <ArrowRight className="w-3 h-3 text-neutral-400 mt-0.5 flex-shrink-0" />
                                      {reason}
                                    </li>
                                  ))}
                                </ul>
                              </div>

                              {/* Deadlines */}
                              {triage.deadlines && triage.deadlines.length > 0 && (
                                <div>
                                  <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-1.5">
                                    Delais detectes
                                  </p>
                                  <div className="space-y-1.5">
                                    {triage.deadlines.map((deadline, idx) => (
                                      <div
                                        key={idx}
                                        className={`flex items-center gap-2 px-2.5 py-1.5 rounded ${
                                          deadlineBadgeColor(deadline.days_remaining)
                                        }`}
                                      >
                                        <Clock className="w-3.5 h-3.5 flex-shrink-0" />
                                        <span className="text-xs font-medium">
                                          {deadline.description}
                                        </span>
                                        <span className="text-xs">
                                          -- {deadline.date}
                                        </span>
                                        <span className="text-xs font-bold ml-auto">
                                          {deadline.days_remaining}j restants
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Case Suggestions */}
                              {triage.suggestions && triage.suggestions.length > 0 && (
                                <div>
                                  <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-1.5">
                                    Dossiers suggeres
                                  </p>
                                  <div className="space-y-1.5">
                                    {triage.suggestions.map((suggestion, idx) => (
                                      <div
                                        key={idx}
                                        className="flex items-center justify-between gap-2 bg-white border border-neutral-200 rounded px-3 py-2"
                                      >
                                        <div className="min-w-0">
                                          <p className="text-xs font-medium text-neutral-800 truncate">
                                            {suggestion.case_reference
                                              ? `${suggestion.case_reference} -- ${suggestion.case_title || ""}`
                                              : suggestion.case_title || "Dossier suggere"}
                                          </p>
                                          <p className="text-[10px] text-neutral-400">
                                            Pertinence : {Math.round(suggestion.relevance * 100)}%
                                          </p>
                                        </div>
                                        {suggestion.case_id && (
                                          <Button
                                            size="sm"
                                            variant="secondary"
                                            icon={<Link2 className="w-3 h-3" />}
                                            onClick={() => handleLinkToCase(item.id, suggestion.case_id!)}
                                            loading={linkingCaseItemId === item.id}
                                            disabled={linkingCaseItemId === item.id}
                                          >
                                            Lier au dossier
                                          </Button>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* No suggestions fallback */}
                              {(!triage.suggestions || triage.suggestions.length === 0) &&
                                (!triage.deadlines || triage.deadlines.length === 0) && (
                                <p className="text-xs text-neutral-400 italic">
                                  Aucun dossier lie ou delai detecte pour cet element.
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
