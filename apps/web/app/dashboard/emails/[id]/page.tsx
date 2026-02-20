"use client";

import { useAuth } from "@/lib/useAuth";
import { useRouter } from "next/navigation";
import { useState, useEffect, useCallback } from "react";
import {
  ArrowLeft,
  Mail,
  Paperclip,
  Download,
  Link as LinkIcon,
  Calendar,
  User,
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Brain,
  Shield,
  Clock,
  Target,
  Zap,
  FileWarning,
  Scale,
  ListChecks,
} from "lucide-react";
import { useThreadEmails, useLinkEmailToCase } from "@/lib/hooks/useEmails";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";

/* ---------- AI Analysis Types ---------- */

interface ClassifyResponse {
  category: string;
  confidence: number;
  reasons: string[];
  suggested_priority: string;
}

interface DeadlineItem {
  text: string;
  date: string;
  deadline_type: string;
  confidence: number;
  source_text: string;
  days: number;
}

interface DeadlineResponse {
  deadlines: DeadlineItem[];
}

/* ---------- Reason translations ---------- */

const REASON_LABELS: Record<string, string> = {
  deadline_keyword: "Mot-cle de delai detecte",
  urgency_keyword: "Terme d'urgence detecte",
  court_keyword: "Reference judiciaire",
  legal_process: "Acte de procedure",
  formal_notice: "Mise en demeure",
  professional_sender: "Expediteur professionnel",
};

/* ---------- Classification display config ---------- */

const CATEGORY_CONFIG: Record<string, { label: string; color: string; icon: typeof Shield }> = {
  urgent: {
    label: "Urgent",
    color: "bg-red-100 text-red-800 border-red-300",
    icon: Zap,
  },
  normal: {
    label: "Normal",
    color: "bg-blue-100 text-blue-800 border-blue-300",
    icon: Mail,
  },
  informatif: {
    label: "Informatif",
    color: "bg-green-100 text-green-800 border-green-300",
    icon: FileWarning,
  },
  spam: {
    label: "Spam",
    color: "bg-neutral-100 text-neutral-600 border-neutral-300",
    icon: Shield,
  },
};

const PRIORITY_LABELS: Record<string, string> = {
  high: "Haute",
  medium: "Moyenne",
  low: "Basse",
};

/* ---------- Suggested actions based on classification ---------- */

function getSuggestedActions(category: string): { label: string; description: string }[] {
  switch (category) {
    case "urgent":
      return [
        { label: "Repondre immediatement", description: "Ce message necessite une reponse rapide." },
        { label: "Creer une tache prioritaire", description: "Planifier un suivi en urgence." },
        { label: "Lier au dossier", description: "Associer a un dossier existant pour suivi." },
      ];
    case "normal":
      return [
        { label: "Repondre dans les 48h", description: "Delai de reponse standard." },
        { label: "Lier au dossier", description: "Associer a un dossier pour archivage." },
      ];
    case "informatif":
      return [
        { label: "Archiver", description: "Classer pour reference future." },
        { label: "Lier au dossier", description: "Associer si pertinent." },
      ];
    case "spam":
      return [
        { label: "Marquer comme spam", description: "Exclure des communications du cabinet." },
      ];
    default:
      return [];
  }
}

/* ---------- Mock fallback classifier ---------- */

function mockClassify(subject: string, body: string): ClassifyResponse {
  const text = `${subject} ${body}`.toLowerCase();
  const reasons: string[] = [];
  let score = 0;

  const deadlineWords = ["delai", "deadline", "echeance", "expiration", "date limite", "avant le"];
  const urgencyWords = ["urgent", "immediatement", "sans delai", "en urgence", "asap", "imperativement"];
  const courtWords = ["tribunal", "cour", "greffe", "audience", "jugement", "arret", "ordonnance", "citation"];
  const processWords = ["assignation", "conclusions", "requete", "appel", "pourvoi", "signification"];
  const formalNotice = ["mise en demeure", "sommation", "injonction", "commandement"];
  const proSenders = ["avocat", "huissier", "notaire", "greffier", "magistrat"];

  if (deadlineWords.some((w) => text.includes(w))) {
    reasons.push("deadline_keyword");
    score += 2;
  }
  if (urgencyWords.some((w) => text.includes(w))) {
    reasons.push("urgency_keyword");
    score += 3;
  }
  if (courtWords.some((w) => text.includes(w))) {
    reasons.push("court_keyword");
    score += 2;
  }
  if (processWords.some((w) => text.includes(w))) {
    reasons.push("legal_process");
    score += 2;
  }
  if (formalNotice.some((w) => text.includes(w))) {
    reasons.push("formal_notice");
    score += 3;
  }
  if (proSenders.some((w) => text.includes(w))) {
    reasons.push("professional_sender");
    score += 1;
  }

  let category: string;
  let confidence: number;
  let suggested_priority: string;

  if (score >= 5) {
    category = "urgent";
    confidence = Math.min(0.95, 0.6 + score * 0.05);
    suggested_priority = "high";
  } else if (score >= 2) {
    category = "normal";
    confidence = Math.min(0.85, 0.5 + score * 0.07);
    suggested_priority = "medium";
  } else if (score >= 1) {
    category = "informatif";
    confidence = 0.55;
    suggested_priority = "low";
  } else {
    category = "informatif";
    confidence = 0.4;
    suggested_priority = "low";
  }

  return { category, confidence, reasons, suggested_priority };
}

export default function EmailThreadPage({ params }: { params: { id: string } }) {
  const { accessToken, tenantId } = useAuth();
  const router = useRouter();
  const token = accessToken;

  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set());
  const [linkingCaseId, setLinkingCaseId] = useState("");
  const [showLinkDialog, setShowLinkDialog] = useState(false);

  /* AI analysis state */
  const [classification, setClassification] = useState<ClassifyResponse | null>(null);
  const [deadlines, setDeadlines] = useState<DeadlineResponse | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiPanelOpen, setAiPanelOpen] = useState(true);

  const emailsQuery = useThreadEmails(params.id, token, tenantId);
  const linkMutation = useLinkEmailToCase(token, tenantId);

  /* ---------- AI Analysis Effect ---------- */
  const runAiAnalysis = useCallback(
    async (subject: string, bodyText: string, fromEmail: string) => {
      if (!token) return;
      setAiLoading(true);

      // Run classification and deadline extraction in parallel
      const classifyPromise = apiFetch<ClassifyResponse>("/ml/classify", token, {
        tenantId,
        method: "POST",
        body: JSON.stringify({ subject, body: bodyText, sender: fromEmail }),
      })
        .then((res) => setClassification(res))
        .catch(() => {
          // Fallback to mock classification
          setClassification(mockClassify(subject, bodyText));
        });

      const deadlinePromise = apiFetch<DeadlineResponse>("/ml/deadlines", token, {
        tenantId,
        method: "POST",
        body: JSON.stringify({ text: `${subject} ${bodyText}` }),
      })
        .then((res) => setDeadlines(res))
        .catch(() => setDeadlines({ deadlines: [] }));

      await Promise.allSettled([classifyPromise, deadlinePromise]);
      setAiLoading(false);
    },
    [token, tenantId],
  );

  useEffect(() => {
    if (emailsQuery.data && emailsQuery.data.items.length > 0 && token && !classification) {
      // Combine all messages for analysis, prioritizing the most recent
      const messages = emailsQuery.data.items;
      const latest = messages[messages.length - 1];
      const allBodies = messages.map((m) => m.body_text).join("\n---\n");
      runAiAnalysis(latest.subject || "", allBodies, latest.from_email);
    }
  }, [emailsQuery.data, token, classification, runAiAnalysis]);

  const toggleMessage = (messageId: string) => {
    const newExpanded = new Set(expandedMessages);
    if (newExpanded.has(messageId)) {
      newExpanded.delete(messageId);
    } else {
      newExpanded.add(messageId);
    }
    setExpandedMessages(newExpanded);
  };

  const handleDownloadAttachment = async (url: string, filename: string) => {
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(objectUrl);
      toast.success("Pièce jointe téléchargée");
    } catch (error) {
      toast.error("Erreur de téléchargement");
    }
  };

  const handleLinkToCase = (emailId: string) => {
    if (!linkingCaseId.trim()) {
      toast.error("Veuillez entrer un ID de dossier");
      return;
    }

    linkMutation.mutate(
      { emailId, caseId: linkingCaseId },
      {
        onSuccess: () => {
          toast.success("Email lié au dossier");
          setShowLinkDialog(false);
          setLinkingCaseId("");
        },
        onError: (error: Error) => {
          toast.error(error.message);
        },
      }
    );
  };

  if (emailsQuery.isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (emailsQuery.isError || !emailsQuery.data) {
    return (
      <div>
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-neutral-600 hover:text-neutral-900 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Retour
        </button>
        <div className="bg-red-50 rounded-lg p-6 border border-red-200">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-6 w-6 text-red-600" />
            <div>
              <h3 className="font-semibold text-red-900">Erreur de chargement</h3>
              <p className="text-sm text-red-700 mt-1">
                Impossible de charger la conversation.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const messages = emailsQuery.data.items.sort(
    (a, b) => new Date(a.sent_at).getTime() - new Date(b.sent_at).getTime()
  );

  const firstMessage = messages[0];

  return (
    <div>
      {/* Header */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-neutral-600 hover:text-neutral-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Retour aux emails
      </button>

      {/* Subject */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900 mb-2">
          {firstMessage.subject || "(Pas de sujet)"}
        </h1>
        <div className="flex items-center gap-4 text-sm text-neutral-600">
          <span className="flex items-center gap-1">
            <Mail className="w-4 h-4" />
            {messages.length} message{messages.length > 1 ? "s" : ""}
          </span>
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            {new Date(firstMessage.sent_at).toLocaleDateString("fr-BE")} -{" "}
            {new Date(messages[messages.length - 1].sent_at).toLocaleDateString("fr-BE")}
          </span>
        </div>
      </div>

      {/* Messages */}
      <div className="space-y-4 mb-6">
        {messages.map((message, index) => {
          const isExpanded = expandedMessages.has(message.id) || index === messages.length - 1;

          return (
            <div key={message.id} className="card">
              {/* Message header */}
              <button
                onClick={() => toggleMessage(message.id)}
                className="w-full flex items-start justify-between hover:bg-neutral-50 -m-6 p-6 rounded-lg transition-colors"
              >
                <div className="flex items-start gap-4 flex-1">
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <User className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="flex-1 text-left">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-neutral-900">
                        {message.from_name || message.from_email}
                      </h3>
                      {message.has_attachments && (
                        <Paperclip className="w-4 h-4 text-neutral-400" />
                      )}
                    </div>
                    <p className="text-sm text-neutral-600">
                      À: {message.to_emails.join(", ")}
                    </p>
                    {message.cc_emails.length > 0 && (
                      <p className="text-sm text-neutral-500">
                        Cc: {message.cc_emails.join(", ")}
                      </p>
                    )}
                    {!isExpanded && (
                      <p className="text-sm text-neutral-500 mt-2 line-clamp-1">
                        {message.body_text.slice(0, 100)}...
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-neutral-500">
                      {new Date(message.sent_at).toLocaleString("fr-BE")}
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="w-5 h-5 text-neutral-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-neutral-400" />
                    )}
                  </div>
                </div>
              </button>

              {/* Message body - Using text only for security (backend should sanitize HTML) */}
              {isExpanded && (
                <div className="mt-4 pt-4 border-t border-neutral-200">
                  <pre className="whitespace-pre-wrap text-sm text-neutral-700 font-sans">
                    {message.body_text}
                  </pre>
                  {message.body_html && (
                    <div className="mt-2 text-xs text-neutral-500 italic">
                      Note: Vue HTML désactivée pour des raisons de sécurité
                    </div>
                  )}

                  {/* Attachments */}
                  {message.attachments.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-neutral-200">
                      <h4 className="text-sm font-semibold text-neutral-900 mb-3">
                        Pièces jointes ({message.attachments.length})
                      </h4>
                      <div className="space-y-2">
                        {message.attachments.map((attachment) => (
                          <div
                            key={attachment.id}
                            className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg"
                          >
                            <div className="flex items-center gap-3">
                              <Paperclip className="w-4 h-4 text-neutral-600" />
                              <div>
                                <p className="text-sm font-medium text-neutral-900">
                                  {attachment.filename}
                                </p>
                                <p className="text-xs text-neutral-500">
                                  {(attachment.size_bytes / 1024).toFixed(1)} KB
                                </p>
                              </div>
                            </div>
                            <button
                              onClick={() =>
                                handleDownloadAttachment(
                                  attachment.download_url,
                                  attachment.filename
                                )
                              }
                              className="p-2 hover:bg-neutral-200 rounded transition-colors"
                            >
                              <Download className="w-4 h-4 text-neutral-600" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="mt-4 pt-4 border-t border-neutral-200 flex gap-2">
                    {!message.case_id && (
                      <button
                        onClick={() => setShowLinkDialog(true)}
                        className="btn-secondary flex items-center gap-2"
                      >
                        <LinkIcon className="w-4 h-4" />
                        Lier à un dossier
                      </button>
                    )}
                    {message.case_id && (
                      <button
                        onClick={() => router.push(`/dashboard/cases/${message.case_id}`)}
                        className="btn-secondary flex items-center gap-2"
                      >
                        <ExternalLink className="w-4 h-4" />
                        Voir le dossier
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* AI Analysis Panel */}
      <div className="card mb-6">
        <button
          onClick={() => setAiPanelOpen(!aiPanelOpen)}
          className="w-full flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-50 rounded-lg">
              <Brain className="w-5 h-5 text-purple-600" />
            </div>
            <h2 className="text-lg font-semibold text-neutral-900">Analyse IA</h2>
            {aiLoading && <Loader2 className="w-4 h-4 animate-spin text-neutral-400" />}
          </div>
          {aiPanelOpen ? (
            <ChevronUp className="w-5 h-5 text-neutral-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-neutral-400" />
          )}
        </button>

        {aiPanelOpen && (
          <div className="mt-6 space-y-6">
            {/* Classification */}
            {classification ? (
              <div className="space-y-4">
                {/* Category badge and confidence */}
                <div>
                  <h3 className="text-sm font-semibold text-neutral-700 mb-3">Classification</h3>
                  <div className="flex items-center gap-3 flex-wrap">
                    {(() => {
                      const config = CATEGORY_CONFIG[classification.category] || CATEGORY_CONFIG.normal;
                      const Icon = config.icon;
                      return (
                        <span
                          className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border ${config.color}`}
                        >
                          <Icon className="w-4 h-4" />
                          {config.label}
                        </span>
                      );
                    })()}
                    <span className="text-sm text-neutral-500">
                      Confiance : {(classification.confidence * 100).toFixed(0)}%
                    </span>
                    <span className="text-sm text-neutral-500">
                      Priorite suggeree :{" "}
                      <span className="font-medium text-neutral-700">
                        {PRIORITY_LABELS[classification.suggested_priority] || classification.suggested_priority}
                      </span>
                    </span>
                  </div>
                </div>

                {/* Confidence progress bar */}
                <div>
                  <div className="w-full bg-neutral-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        classification.confidence >= 0.8
                          ? "bg-green-500"
                          : classification.confidence >= 0.5
                            ? "bg-yellow-500"
                            : "bg-red-500"
                      }`}
                      style={{ width: `${classification.confidence * 100}%` }}
                    />
                  </div>
                </div>

                {/* Reasons */}
                {classification.reasons.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-700 mb-2">
                      Raisons de la classification
                    </h3>
                    <ul className="space-y-1.5">
                      {classification.reasons.map((reason, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm text-neutral-600">
                          <Target className="w-3.5 h-3.5 text-purple-500 flex-shrink-0" />
                          {REASON_LABELS[reason] || reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Suggested actions */}
                {(() => {
                  const actions = getSuggestedActions(classification.category);
                  if (actions.length === 0) return null;
                  return (
                    <div>
                      <h3 className="text-sm font-semibold text-neutral-700 mb-2">
                        Actions suggerees
                      </h3>
                      <div className="space-y-2">
                        {actions.map((action, i) => (
                          <div
                            key={i}
                            className="flex items-start gap-3 p-3 bg-neutral-50 rounded-lg"
                          >
                            <ListChecks className="w-4 h-4 text-accent mt-0.5 flex-shrink-0" />
                            <div>
                              <p className="text-sm font-medium text-neutral-800">{action.label}</p>
                              <p className="text-xs text-neutral-500">{action.description}</p>
                            </div>
                            {action.label === "Lier au dossier" && !firstMessage.case_id && (
                              <button
                                onClick={() => setShowLinkDialog(true)}
                                className="ml-auto text-xs text-accent hover:text-accent-600 font-medium whitespace-nowrap"
                              >
                                Lier maintenant
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </div>
            ) : aiLoading ? (
              <div className="flex items-center gap-3 py-4">
                <Loader2 className="w-5 h-5 animate-spin text-purple-500" />
                <span className="text-sm text-neutral-600">Analyse en cours...</span>
              </div>
            ) : (
              <p className="text-sm text-neutral-500">Analyse non disponible.</p>
            )}

            {/* Deadlines */}
            <div>
              <h3 className="text-sm font-semibold text-neutral-700 mb-2 flex items-center gap-2">
                <Clock className="w-4 h-4 text-orange-500" />
                Delais extraits
              </h3>
              {deadlines && deadlines.deadlines.length > 0 ? (
                <div className="space-y-2">
                  {deadlines.deadlines.map((dl, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 p-3 bg-orange-50 border border-orange-200 rounded-lg"
                    >
                      <Scale className="w-4 h-4 text-orange-600 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-sm font-medium text-neutral-800">{dl.text}</p>
                          <span className="text-xs px-2 py-0.5 rounded-full bg-orange-100 text-orange-700">
                            {dl.deadline_type}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 mt-1">
                          <p className="text-xs text-neutral-600">
                            Date : {new Date(dl.date).toLocaleDateString("fr-BE")}
                          </p>
                          {dl.days !== undefined && (
                            <p
                              className={`text-xs font-medium ${
                                dl.days <= 3
                                  ? "text-red-600"
                                  : dl.days <= 7
                                    ? "text-orange-600"
                                    : "text-neutral-600"
                              }`}
                            >
                              {dl.days <= 0
                                ? "Expire"
                                : dl.days === 1
                                  ? "Demain"
                                  : `Dans ${dl.days} jours`}
                            </p>
                          )}
                          <p className="text-xs text-neutral-500">
                            Confiance : {(dl.confidence * 100).toFixed(0)}%
                          </p>
                        </div>
                        {dl.source_text && (
                          <p className="text-xs text-neutral-400 mt-1 italic">
                            &laquo; {dl.source_text} &raquo;
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : deadlines ? (
                <p className="text-sm text-neutral-500 py-2">
                  Aucun delai detecte dans cet email.
                </p>
              ) : aiLoading ? (
                <div className="flex items-center gap-2 py-2">
                  <Loader2 className="w-4 h-4 animate-spin text-orange-400" />
                  <span className="text-sm text-neutral-500">Extraction en cours...</span>
                </div>
              ) : (
                <p className="text-sm text-neutral-500 py-2">Analyse non disponible.</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Link to case dialog */}
      {showLinkDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-neutral-900 mb-4">
              Lier au dossier
            </h3>
            <input
              type="text"
              value={linkingCaseId}
              onChange={(e) => setLinkingCaseId(e.target.value)}
              placeholder="ID du dossier..."
              className="input w-full mb-4"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setShowLinkDialog(false);
                  setLinkingCaseId("");
                }}
                className="btn-secondary"
              >
                Annuler
              </button>
              <button
                onClick={() => handleLinkToCase(firstMessage.id)}
                disabled={linkMutation.isPending}
                className="btn-primary"
              >
                {linkMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  "Lier"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
