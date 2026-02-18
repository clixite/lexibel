"use client";

import { useAuth } from "@/lib/useAuth";
import { useRouter } from "next/navigation";
import { useState } from "react";
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
} from "lucide-react";
import { useThreadEmails, useLinkEmailToCase } from "@/lib/hooks/useEmails";
import { toast } from "sonner";

export default function EmailThreadPage({ params }: { params: { id: string } }) {
  const { accessToken, tenantId } = useAuth();
  const router = useRouter();
  const token = accessToken;

  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set());
  const [linkingCaseId, setLinkingCaseId] = useState("");
  const [showLinkDialog, setShowLinkDialog] = useState(false);

  const emailsQuery = useThreadEmails(params.id, token, tenantId);
  const linkMutation = useLinkEmailToCase(token, tenantId);

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
