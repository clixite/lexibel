"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Phone,
  PhoneIncoming,
  PhoneOutgoing,
  PhoneMissed,
  Voicemail,
  Clock,
  FileText,
  Mic,
  Smile,
  Meh,
  Frown,
  Calendar,
  Filter,
  Loader2,
  Download,
  AlertCircle,
} from "lucide-react";
import { useRingoverCalls } from "@/lib/hooks/useRingoverCalls";
import { useRingoverStats } from "@/lib/hooks/useRingoverStats";
import type { CallListFilters } from "@/lib/api/ringover";
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
  positive: "text-green-600",
  neutral: "text-neutral-600",
  negative: "text-red-600",
};

export default function CallsPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const user = session?.user as any;
  const token = user?.accessToken;
  const tenantId = user?.tenantId;

  const [filters, setFilters] = useState<CallListFilters>({
    page: 1,
    per_page: 20,
  });
  const [statsDays, setStatsDays] = useState(30);

  // Hooks
  const callsQuery = useRingoverCalls(filters, token, tenantId);
  const statsQuery = useRingoverStats(statsDays, undefined, token, tenantId);

  const handleDownloadRecording = async (recordingUrl: string, fileName: string) => {
    try {
      const response = await fetch(recordingUrl);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${fileName}.mp3`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Enregistrement téléchargé");
    } catch (error) {
      toast.error("Erreur de téléchargement");
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Appels téléphoniques</h1>
          <p className="text-neutral-500 text-sm mt-1">
            Historique et statistiques Ringover
          </p>
        </div>
      </div>

      {/* Stats Grid */}
      {statsQuery.data && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
          <div className="card">
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-md bg-accent-50">
                <Phone className="w-5 h-5 text-accent" />
              </div>
            </div>
            <div className="mt-4">
              <p className="text-2xl font-bold text-neutral-900">
                {statsQuery.data.total_calls}
              </p>
              <p className="text-sm text-neutral-500 mt-0.5">Total appels</p>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-md bg-green-50">
                <Phone className="w-5 h-5 text-green-600" />
              </div>
            </div>
            <div className="mt-4">
              <p className="text-2xl font-bold text-neutral-900">
                {statsQuery.data.answered_calls}
              </p>
              <p className="text-sm text-neutral-500 mt-0.5">Répondus</p>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-md bg-red-50">
                <PhoneMissed className="w-5 h-5 text-red-600" />
              </div>
            </div>
            <div className="mt-4">
              <p className="text-2xl font-bold text-neutral-900">
                {statsQuery.data.missed_calls}
              </p>
              <p className="text-sm text-neutral-500 mt-0.5">Manqués</p>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-md bg-blue-50">
                <Clock className="w-5 h-5 text-blue-600" />
              </div>
            </div>
            <div className="mt-4">
              <p className="text-2xl font-bold text-neutral-900">
                {Math.round(statsQuery.data.total_duration_minutes)}m
              </p>
              <p className="text-sm text-neutral-500 mt-0.5">Durée totale</p>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <select
          className="px-4 py-2 border border-neutral-200 rounded-lg text-sm"
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              direction: e.target.value || undefined,
            }))
          }
        >
          <option value="">Toutes directions</option>
          <option value="inbound">Entrant</option>
          <option value="outbound">Sortant</option>
        </select>

        <select
          className="px-4 py-2 border border-neutral-200 rounded-lg text-sm"
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              call_type: e.target.value as any || undefined,
            }))
          }
        >
          <option value="">Tous types</option>
          <option value="answered">Répondus</option>
          <option value="missed">Manqués</option>
          <option value="voicemail">Messages vocaux</option>
        </select>

        <select
          className="px-4 py-2 border border-neutral-200 rounded-lg text-sm"
          value={statsDays}
          onChange={(e) => setStatsDays(Number(e.target.value))}
        >
          <option value="7">7 derniers jours</option>
          <option value="30">30 derniers jours</option>
          <option value="90">90 derniers jours</option>
        </select>
      </div>

      {/* Calls List */}
      {callsQuery.isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
        </div>
      )}

      {callsQuery.isError && (
        <div className="bg-red-50 rounded-lg p-6 border border-red-200">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-6 w-6 text-red-600" />
            <div>
              <h3 className="font-semibold text-red-900">Erreur de chargement</h3>
              <p className="text-sm text-red-700 mt-1">
                Impossible de charger les appels. Veuillez réessayer.
              </p>
            </div>
          </div>
        </div>
      )}

      {callsQuery.data && callsQuery.data.items.length === 0 && (
        <div className="bg-white rounded-lg p-12 text-center border border-neutral-200">
          <Phone className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-neutral-600 mb-2">
            Aucun appel
          </h3>
          <p className="text-neutral-500">
            {filters.direction || filters.call_type
              ? "Essayez de modifier vos filtres."
              : "Aucun appel enregistré pour le moment."}
          </p>
        </div>
      )}

      {callsQuery.data && callsQuery.data.items.length > 0 && (
        <div className="space-y-4">
          {callsQuery.data.items.map((call) => {
            const TypeIcon = CALL_TYPE_ICONS[call.call_type];
            const DirectionIcon = call.direction === "inbound" ? PhoneIncoming : PhoneOutgoing;
            const SentimentIcon = call.sentiment ? SENTIMENT_ICONS[call.sentiment] : null;

            return (
              <div
                key={call.id}
                className="card hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => router.push(`/dashboard/calls/${call.id}`)}
              >
                <div className="flex items-start gap-4">
                  {/* Icon */}
                  <div className={`p-3 rounded-lg ${CALL_TYPE_COLORS[call.call_type]}`}>
                    <TypeIcon className="w-6 h-6" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-neutral-900">
                            {call.contact_name || call.phone_number}
                          </h3>
                          <DirectionIcon className="w-4 h-4 text-neutral-400" />
                          <span
                            className={`px-2 py-0.5 rounded-full text-xs font-medium ${CALL_TYPE_COLORS[call.call_type].replace("text-", "bg-").replace("bg-", "text-")}`}
                          >
                            {CALL_TYPE_LABELS[call.call_type]}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-neutral-500">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5" />
                            {call.duration_formatted}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5" />
                            {new Date(call.occurred_at).toLocaleString("fr-BE")}
                          </span>
                          {!call.contact_name && (
                            <span className="text-neutral-400">{call.phone_number}</span>
                          )}
                        </div>
                      </div>

                      {/* Sentiment */}
                      {SentimentIcon && (
                        <div className="flex items-center gap-1">
                          <SentimentIcon
                            className={`w-5 h-5 ${SENTIMENT_COLORS[call.sentiment!]}`}
                          />
                        </div>
                      )}
                    </div>

                    {/* AI Summary */}
                    {call.ai_summary && (
                      <div className="bg-blue-50 rounded-lg p-3 mb-3 border border-blue-200">
                        <p className="text-sm text-blue-900 leading-relaxed">
                          {call.ai_summary}
                        </p>
                      </div>
                    )}

                    {/* Features */}
                    <div className="flex items-center gap-4 text-sm">
                      {call.has_recording && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (call.recording_url) {
                              handleDownloadRecording(
                                call.recording_url,
                                `call_${call.id}`
                              );
                            }
                          }}
                          className="flex items-center gap-1 text-accent hover:text-accent-600 transition-colors"
                        >
                          <Download className="w-3.5 h-3.5" />
                          Enregistrement
                        </button>
                      )}
                      {call.has_transcript && (
                        <span className="flex items-center gap-1 text-green-600">
                          <FileText className="w-3.5 h-3.5" />
                          Transcription
                        </span>
                      )}
                      {call.tasks_count > 0 && (
                        <span className="text-neutral-600">
                          {call.tasks_count} tâche{call.tasks_count > 1 ? "s" : ""}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {callsQuery.data && callsQuery.data.total > callsQuery.data.per_page && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() =>
              setFilters((prev) => ({ ...prev, page: (prev.page || 1) - 1 }))
            }
            disabled={(filters.page || 1) <= 1}
            className="btn-secondary disabled:opacity-50"
          >
            Précédent
          </button>
          <span className="text-sm text-neutral-600">
            Page {filters.page || 1} sur{" "}
            {Math.ceil(callsQuery.data.total / callsQuery.data.per_page)}
          </span>
          <button
            onClick={() =>
              setFilters((prev) => ({ ...prev, page: (prev.page || 1) + 1 }))
            }
            disabled={
              (filters.page || 1) >=
              Math.ceil(callsQuery.data.total / callsQuery.data.per_page)
            }
            className="btn-secondary disabled:opacity-50"
          >
            Suivant
          </button>
        </div>
      )}
    </div>
  );
}
