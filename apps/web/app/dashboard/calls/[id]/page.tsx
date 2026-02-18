"use client";

import { useAuth } from "@/lib/useAuth";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Phone,
  PhoneIncoming,
  PhoneOutgoing,
  PhoneMissed,
  Voicemail,
  Clock,
  Calendar,
  FileText,
  Download,
  Mic,
  User,
  Briefcase,
  ArrowLeft,
  Loader2,
  AlertCircle,
  Smile,
  Meh,
  Frown,
  CheckCircle,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { CallEvent } from "@/lib/api/ringover";
import { toast } from "sonner";

const CALL_TYPE_ICONS = {
  answered: Phone,
  missed: PhoneMissed,
  voicemail: Voicemail,
};

const CALL_TYPE_LABELS = {
  answered: "Répondu",
  missed: "Manqué",
  voicemail: "Message vocal",
};

const CALL_TYPE_COLORS = {
  answered: "text-green-600 bg-green-50",
  missed: "text-red-600 bg-red-50",
  voicemail: "text-blue-600 bg-blue-50",
};

const SENTIMENT_ICONS = {
  positive: Smile,
  neutral: Meh,
  negative: Frown,
};

const SENTIMENT_COLORS = {
  positive: "text-green-600 bg-green-50",
  neutral: "text-neutral-600 bg-neutral-50",
  negative: "text-red-600 bg-red-50",
};

const SENTIMENT_LABELS = {
  positive: "Positif",
  neutral: "Neutre",
  negative: "Négatif",
};

export default function CallDetailPage({ params }: { params: { id: string } }) {
  const { accessToken, tenantId } = useAuth();
  const router = useRouter();
  const token = accessToken;

  const callQuery = useQuery({
    queryKey: ["ringover-call", params.id, tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      return apiFetch<CallEvent>(`/ringover/calls/${params.id}`, token, {
        tenantId,
      });
    },
    enabled: !!token,
  });

  const handleDownloadRecording = async (recordingUrl: string) => {
    try {
      const response = await fetch(recordingUrl);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `call_${params.id}.mp3`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Enregistrement téléchargé");
    } catch (error) {
      toast.error("Erreur de téléchargement");
    }
  };

  const handleDownloadTranscript = (transcript: string) => {
    const blob = new Blob([transcript], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `call_${params.id}_transcript.txt`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Transcription téléchargée");
  };

  if (callQuery.isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (callQuery.isError || !callQuery.data) {
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
                Impossible de charger les détails de l'appel.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const call = callQuery.data;
  const TypeIcon = CALL_TYPE_ICONS[call.call_type];
  const DirectionIcon = call.direction === "inbound" ? PhoneIncoming : PhoneOutgoing;
  const SentimentIcon = call.sentiment ? SENTIMENT_ICONS[call.sentiment] : null;

  return (
    <div>
      {/* Header */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-neutral-600 hover:text-neutral-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Retour aux appels
      </button>

      {/* Main Card */}
      <div className="card mb-6">
        <div className="flex items-start gap-4 mb-6">
          <div className={`p-4 rounded-lg ${CALL_TYPE_COLORS[call.call_type]}`}>
            <TypeIcon className="w-8 h-8" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <h1 className="text-2xl font-bold text-neutral-900">
                {call.contact_name || call.phone_number}
              </h1>
              <DirectionIcon className="w-5 h-5 text-neutral-400" />
              <span
                className={`px-2 py-1 rounded-full text-xs font-medium ${CALL_TYPE_COLORS[call.call_type].replace("text-", "bg-").replace("bg-", "text-")}`}
              >
                {CALL_TYPE_LABELS[call.call_type]}
              </span>
            </div>
            <div className="flex items-center gap-4 text-sm text-neutral-500">
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {new Date(call.occurred_at).toLocaleString("fr-BE", {
                  dateStyle: "full",
                  timeStyle: "short",
                })}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                {call.duration_formatted}
              </span>
            </div>
          </div>
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {call.contact_id && (
            <div className="flex items-center gap-3 p-4 bg-neutral-50 rounded-lg">
              <User className="w-5 h-5 text-neutral-600" />
              <div>
                <p className="text-xs text-neutral-500">Contact</p>
                <p className="font-medium text-neutral-900">{call.contact_name}</p>
              </div>
            </div>
          )}
          {call.case_id && (
            <div className="flex items-center gap-3 p-4 bg-neutral-50 rounded-lg">
              <Briefcase className="w-5 h-5 text-neutral-600" />
              <div>
                <p className="text-xs text-neutral-500">Dossier lié</p>
                <button
                  onClick={() => router.push(`/dashboard/cases/${call.case_id}`)}
                  className="font-medium text-accent hover:text-accent-600"
                >
                  Voir le dossier →
                </button>
              </div>
            </div>
          )}
          {call.sentiment && SentimentIcon && (
            <div
              className={`flex items-center gap-3 p-4 rounded-lg ${SENTIMENT_COLORS[call.sentiment]}`}
            >
              <SentimentIcon className="w-5 h-5" />
              <div>
                <p className="text-xs opacity-80">Sentiment</p>
                <p className="font-medium">{SENTIMENT_LABELS[call.sentiment]}</p>
              </div>
            </div>
          )}
        </div>

        {/* AI Summary */}
        {call.ai_summary && (
          <div className="bg-blue-50 rounded-lg p-4 border border-blue-200 mb-6">
            <div className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-blue-900 mb-2">Résumé IA</h3>
                <p className="text-blue-800 leading-relaxed">{call.ai_summary}</p>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          {call.has_recording && call.recording_url && (
            <button
              onClick={() => handleDownloadRecording(call.recording_url!)}
              className="btn-primary flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Télécharger l'enregistrement
            </button>
          )}
          {call.has_transcript && call.transcript && (
            <button
              onClick={() => handleDownloadTranscript(call.transcript!)}
              className="btn-secondary flex items-center gap-2"
            >
              <FileText className="w-4 h-4" />
              Télécharger la transcription
            </button>
          )}
        </div>
      </div>

      {/* Transcript */}
      {call.transcript && (
        <div className="card mb-6">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4 flex items-center gap-2">
            <Mic className="w-5 h-5" />
            Transcription
          </h2>
          <div className="bg-neutral-50 rounded-lg p-4 border border-neutral-200">
            <p className="text-neutral-700 leading-relaxed whitespace-pre-wrap">
              {call.transcript}
            </p>
          </div>
        </div>
      )}

      {/* Tasks */}
      {call.tasks_count > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">
            Tâches générées ({call.tasks_count})
          </h2>
          <p className="text-neutral-600 text-sm">
            {call.tasks_count} tâche{call.tasks_count > 1 ? "s ont" : " a"} été générée
            {call.tasks_count > 1 ? "s" : ""} automatiquement à partir de cet appel.
          </p>
        </div>
      )}
    </div>
  );
}
