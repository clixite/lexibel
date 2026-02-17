"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState, useCallback } from "react";
import {
  Inbox,
  Mail,
  Phone,
  FileText,
  Loader2,
  Check,
  X,
  AlertTriangle,
  ChevronDown,
  FolderPlus,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, EmptyState, Badge, Modal } from "@/components/ui";

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
  if (diffMin < 1) return "À l'instant";
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
    `Élément ${item.source}`
  );
}

function generateReference(): string {
  const year = new Date().getFullYear();
  const num = String(Math.floor(Math.random() * 999) + 1).padStart(3, "0");
  return `DOS-${year}-${num}`;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function InboxPage() {
  const { data: session } = useSession();

  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;
  const userId = (session?.user as any)?.id;

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

  /* --- Data loading --- */
  const loadItems = useCallback(() => {
    if (!token) return;
    setLoading(true);
    setError(null);

    const statusParam = statusFilter ? `?status=${statusFilter}` : "";
    apiFetch<InboxListResponse>(`/inbox${statusParam}`, token, { tenantId })
      .then((data) => {
        setItems(data.items);
        setTotalCount(data.total);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token, tenantId, statusFilter]);

  const loadCases = useCallback(() => {
    if (!token) return;
    apiFetch<CaseListResponse>("/cases", token, { tenantId })
      .then((data) => setCases(data.items))
      .catch(() => {});
  }, [token, tenantId]);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  /* --- Actions --- */
  const handleValidate = async () => {
    if (!token || !validateTarget || !validateForm.case_id || !validateForm.title.trim())
      return;
    setActionLoading(validateTarget.id);
    setError(null);
    try {
      await apiFetch(`/inbox/${validateTarget.id}/validate`, token, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          case_id: validateForm.case_id,
          event_type: validateForm.event_type,
          title: validateForm.title,
          body: validateForm.body || undefined,
        }),
      });
      setSuccess("Élément validé et ajouté au dossier.");
      setValidateTarget(null);
      setValidateForm({
        case_id: "",
        event_type: "email_received",
        title: "",
        body: "",
      });
      loadItems();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRefuse = async () => {
    if (!token || !refuseTarget) return;
    setActionLoading(refuseTarget.id);
    setError(null);
    try {
      await apiFetch(`/inbox/${refuseTarget.id}/refuse`, token, {
        tenantId,
        method: "POST",
      });
      setSuccess("Élément refusé.");
      setRefuseTarget(null);
      loadItems();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleCreateCase = async () => {
    if (
      !token ||
      !createCaseTarget ||
      !createCaseForm.title.trim() ||
      !createCaseForm.reference.trim()
    )
      return;
    setActionLoading(createCaseTarget.id);
    setError(null);
    try {
      await apiFetch(`/inbox/${createCaseTarget.id}/create-case`, token, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          reference: createCaseForm.reference,
          title: createCaseForm.title,
          matter_type: createCaseForm.matter_type,
          responsible_user_id: userId,
        }),
      });
      setSuccess("Nouveau dossier créé à partir de cet élément.");
      setCreateCaseTarget(null);
      setCreateCaseForm({
        reference: generateReference(),
        title: "",
        matter_type: "general",
      });
      loadItems();
      loadCases();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  /* Open validate modal with pre-filled data */
  const openValidate = (item: InboxItem) => {
    setValidateForm({
      case_id: item.suggested_case_id || "",
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

  /* --- Filtered items --- */
  const filteredItems = statusFilter
    ? items
    : items; // API already filters; show all when "Tous"

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
      </div>

      {/* Filter tabs */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="flex gap-1 bg-neutral-100 rounded-md p-1">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 ${
                statusFilter === f.value
                  ? "bg-white text-neutral-900 shadow-subtle"
                  : "text-neutral-500 hover:text-neutral-700"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

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
        title="Valider et rattacher à un dossier"
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
                    <option value="">-- Sélectionner un dossier --</option>
                    {cases.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.reference} — {c.title}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 pointer-events-none" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Type d&apos;événement
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
                  placeholder="Titre de l'événement"
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
                  placeholder="Détails supplémentaires..."
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
              Êtes-vous sûr de vouloir refuser cet élément ? Cette action
              marquera l&apos;entrée comme non pertinente.
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
        title="Créer un nouveau dossier"
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
              Créer le dossier
            </button>
          </div>
        }
      >
            <div className="bg-accent-50/50 border border-accent-100 rounded-md p-3 mb-5">
              <p className="text-xs text-accent-600">
                Un dossier sera créé et cet élément y sera automatiquement
                rattaché.
              </p>
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Référence
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
                    Type de matière
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
        <div className="bg-white rounded-lg shadow-subtle overflow-hidden">
          <div className="relative">
            <div className="absolute inset-0 opacity-[0.03]">
              <div
                className="w-full h-full"
                style={{
                  backgroundImage:
                    "radial-gradient(circle at 1px 1px, currentColor 1px, transparent 0)",
                  backgroundSize: "24px 24px",
                }}
              />
            </div>
            <div className="relative px-6 py-20 text-center">
              <EmptyState
                title="Aucun élément"
                description={
                  statusFilter
                    ? "Aucun élément ne correspond à ce filtre. Essayez un autre statut."
                    : "Votre inbox est vide. Les nouveaux e-mails, appels et documents apparaîtront ici automatiquement."
                }
              />
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredItems.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-lg shadow-subtle border border-neutral-100 p-5 hover:border-accent-200 transition-colors duration-150"
            >
              <div className="flex items-start gap-4">
                {/* Source icon */}
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${sourceColor(item.source)}`}
                >
                  {sourceIcon(item.source)}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-neutral-900 truncate">
                        {itemTitle(item)}
                      </h3>
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
                      <span className="text-xs text-neutral-400 whitespace-nowrap">
                        {timeAgo(item.created_at)}
                      </span>
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          statusStyles[item.status] ||
                          "bg-neutral-100 text-neutral-600"
                        }`}
                      >
                        {statusLabels[item.status] || item.status}
                      </span>
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
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-accent-50 text-accent-700 ml-2">
                        Dossier suggéré
                      </span>
                    )}
                  </div>

                  {/* Actions for DRAFT items */}
                  {item.status === "DRAFT" && (
                    <div className="flex items-center gap-2 mt-3 pt-3 border-t border-neutral-100">
                      <button
                        onClick={() => openValidate(item)}
                        disabled={actionLoading === item.id}
                        className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1.5 disabled:opacity-50"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Valider
                      </button>
                      <button
                        onClick={() => setRefuseTarget(item)}
                        disabled={actionLoading === item.id}
                        className="px-3 py-1.5 text-xs font-medium text-danger bg-danger-50 rounded-md hover:bg-danger-100 transition-colors flex items-center gap-1.5 disabled:opacity-50"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        Refuser
                      </button>
                      <button
                        onClick={() => openCreateCase(item)}
                        disabled={actionLoading === item.id}
                        className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 disabled:opacity-50"
                      >
                        <FolderPlus className="w-3.5 h-3.5" />
                        Créer dossier
                      </button>
                      {actionLoading === item.id && (
                        <Loader2 className="w-4 h-4 animate-spin text-accent ml-1" />
                      )}
                    </div>
                  )}

                  {/* Status indicator for processed items */}
                  {item.status === "VALIDATED" && (
                    <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-neutral-100">
                      <CheckCircle2 className="w-4 h-4 text-success" />
                      <span className="text-xs text-success-700">
                        Validé et rattaché à un dossier
                      </span>
                    </div>
                  )}
                  {item.status === "REFUSED" && (
                    <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-neutral-100">
                      <XCircle className="w-4 h-4 text-danger" />
                      <span className="text-xs text-danger-700">
                        Refusé — non rattaché
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
