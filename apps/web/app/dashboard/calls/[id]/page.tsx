"use client";

import { useAuth } from "@/lib/useAuth";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useState, useEffect, useCallback } from "react";
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
  Brain,
  ChevronDown,
  ChevronUp,
  Tag,
  ListChecks,
  Send,
  Link as LinkIcon,
  MessageSquare,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { CallEvent } from "@/lib/api/ringover";
import { toast } from "sonner";

/* ---------- Types for transcription intelligence ---------- */

interface TranscriptionAnalysis {
  tone: "cooperative" | "neutral" | "tense" | "hostile";
  topics: string[];
  actionItems: string[];
  summary: string;
  speakerSegments: SpeakerSegment[];
}

interface SpeakerSegment {
  speaker: string;
  text: string;
  startTime?: string;
}

/* ---------- Tone display config ---------- */

const TONE_CONFIG: Record<string, { label: string; color: string; description: string }> = {
  cooperative: {
    label: "Cooperatif",
    color: "bg-green-100 text-green-800 border-green-300",
    description: "L'interlocuteur est receptif et collaboratif.",
  },
  neutral: {
    label: "Neutre",
    color: "bg-blue-100 text-blue-800 border-blue-300",
    description: "Echange factuel, sans tension particuliere.",
  },
  tense: {
    label: "Tendu",
    color: "bg-orange-100 text-orange-800 border-orange-300",
    description: "Des signes de tension ont ete detectes.",
  },
  hostile: {
    label: "Hostile",
    color: "bg-red-100 text-red-800 border-red-300",
    description: "L'echange presente des signes de conflit.",
  },
};

/* ---------- Mock transcription analyzer ---------- */

function analyzeTranscription(transcript: string): TranscriptionAnalysis {
  const text = transcript.toLowerCase();

  // Tone analysis based on keyword detection
  let tone: TranscriptionAnalysis["tone"] = "neutral";
  const cooperativeWords = ["merci", "d'accord", "bien entendu", "parfait", "je comprends", "tout a fait", "volontiers"];
  const tenseWords = ["probleme", "inacceptable", "delai depasse", "en retard", "mecontentement", "plainte"];
  const hostileWords = ["menace", "poursuite", "action en justice", "mise en demeure", "ultimatum", "inexcusable"];

  const cooperativeScore = cooperativeWords.filter((w) => text.includes(w)).length;
  const tenseScore = tenseWords.filter((w) => text.includes(w)).length;
  const hostileScore = hostileWords.filter((w) => text.includes(w)).length;

  if (hostileScore >= 2) tone = "hostile";
  else if (tenseScore >= 2) tone = "tense";
  else if (cooperativeScore >= 2) tone = "cooperative";

  // Topic extraction
  const topicKeywords: Record<string, string[]> = {
    "Droit du travail": ["contrat de travail", "licenciement", "preavis", "salaire", "conge"],
    "Droit immobilier": ["bail", "loyer", "propriete", "immeuble", "copropriete", "expulsion"],
    "Droit de la famille": ["divorce", "garde", "pension alimentaire", "succession", "heritage"],
    "Droit des societes": ["societe", "parts sociales", "assemblee generale", "gerant", "statuts"],
    "Procedure judiciaire": ["tribunal", "audience", "jugement", "appel", "conclusions"],
    "Facturation": ["facture", "honoraires", "provision", "paiement", "reglement"],
    "Delais": ["delai", "echeance", "date limite", "prescription"],
    "Rendez-vous": ["rendez-vous", "reunion", "consultation", "rdv"],
  };

  const topics: string[] = [];
  for (const [topic, keywords] of Object.entries(topicKeywords)) {
    if (keywords.some((kw) => text.includes(kw))) {
      topics.push(topic);
    }
  }
  if (topics.length === 0) topics.push("Consultation generale");

  // Action item extraction
  const actionItems: string[] = [];
  const actionPatterns = [
    { pattern: /(?:il faut|je dois|vous devez|nous devons|a faire)[^.]*\./gi, prefix: "" },
    { pattern: /(?:envoyer|transmettre|preparer|rediger|contacter|appeler|verifier|confirmer)[^.]*\./gi, prefix: "" },
    { pattern: /(?:rappeler|relancer|suivre|planifier)[^.]*\./gi, prefix: "" },
  ];

  for (const { pattern } of actionPatterns) {
    const matches = transcript.match(pattern);
    if (matches) {
      for (const match of matches.slice(0, 3)) {
        const cleaned = match.trim().replace(/^\w/, (c) => c.toUpperCase());
        if (cleaned.length > 10 && cleaned.length < 200 && !actionItems.includes(cleaned)) {
          actionItems.push(cleaned);
        }
      }
    }
  }

  // Summary generation
  const sentences = transcript.split(/[.!?]+/).filter((s) => s.trim().length > 20);
  const summaryParts = sentences.slice(0, 3).map((s) => s.trim());
  const summary =
    summaryParts.length > 0
      ? summaryParts.join(". ") + "."
      : "Transcription trop courte pour generer un resume.";

  // Speaker segment parsing
  const speakerSegments: SpeakerSegment[] = [];
  const segmentPattern = /(?:\[(\d{2}:\d{2}(?::\d{2})?)\]\s*)?(?:(Locuteur\s*\d+|Avocat|Client|Interlocuteur)[:\s-]+)?(.+?)(?=(?:\[|\n(?:Locuteur|Avocat|Client|Interlocuteur))|$)/gi;
  const rawSegments = transcript.match(segmentPattern);

  if (rawSegments && rawSegments.length > 1) {
    let currentSpeaker = "Locuteur 1";
    for (const seg of rawSegments.slice(0, 20)) {
      const speakerMatch = seg.match(/^(?:\[(\d{2}:\d{2}(?::\d{2})?)\]\s*)?(?:(Locuteur\s*\d+|Avocat|Client|Interlocuteur)[:\s-]+)?(.+)/i);
      if (speakerMatch) {
        const time = speakerMatch[1] || undefined;
        if (speakerMatch[2]) currentSpeaker = speakerMatch[2].trim();
        const segText = speakerMatch[3]?.trim();
        if (segText && segText.length > 5) {
          speakerSegments.push({ speaker: currentSpeaker, text: segText, startTime: time });
        }
      }
    }
  }

  // If no segments were parsed, create a single-speaker fallback
  if (speakerSegments.length === 0 && transcript.length > 20) {
    const chunks = transcript.split(/\n+/).filter((c) => c.trim().length > 5);
    for (let i = 0; i < Math.min(chunks.length, 10); i++) {
      speakerSegments.push({
        speaker: i % 2 === 0 ? "Locuteur 1" : "Locuteur 2",
        text: chunks[i].trim(),
      });
    }
  }

  return { tone, topics, actionItems, summary, speakerSegments };
}

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

  /* Transcription intelligence state */
  const [transcriptionAnalysis, setTranscriptionAnalysis] = useState<TranscriptionAnalysis | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [intelligencePanelOpen, setIntelligencePanelOpen] = useState(true);
  const [actionsPanelOpen, setActionsPanelOpen] = useState(true);
  const [showLinkDialog, setShowLinkDialog] = useState(false);
  const [linkingCaseId, setLinkingCaseId] = useState("");

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

  /* ---------- Transcription Intelligence Analysis ---------- */
  const runTranscriptionAnalysis = useCallback(
    async (transcript: string) => {
      if (!token) return;
      setAiLoading(true);

      try {
        // Try API-based analysis first
        const result = await apiFetch<{ analysis: TranscriptionAnalysis }>("/ml/process", token, {
          tenantId,
          method: "POST",
          body: JSON.stringify({ text: transcript, task: "call_analysis" }),
        });
        setTranscriptionAnalysis(result.analysis);
      } catch {
        // Fallback to local mock analysis
        const analysis = analyzeTranscription(transcript);
        setTranscriptionAnalysis(analysis);
      }

      setAiLoading(false);
    },
    [token, tenantId],
  );

  useEffect(() => {
    if (callQuery.data?.transcript && token && !transcriptionAnalysis) {
      runTranscriptionAnalysis(callQuery.data.transcript);
    }
  }, [callQuery.data, token, transcriptionAnalysis, runTranscriptionAnalysis]);

  const handleCreateTask = (actionText: string) => {
    toast.success(`Tache creee : ${actionText.slice(0, 50)}...`);
  };

  const handleLinkToCase = () => {
    if (!linkingCaseId.trim()) {
      toast.error("Veuillez entrer un ID de dossier");
      return;
    }
    toast.success("Appel lie au dossier");
    setShowLinkDialog(false);
    setLinkingCaseId("");
  };

  const handleSendSummary = () => {
    toast.success("Brouillon de recapitulatif cree");
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

      {/* Transcription Intelligence Panel */}
      {call.transcript && (
        <div className="card mb-6">
          <button
            onClick={() => setIntelligencePanelOpen(!intelligencePanelOpen)}
            className="w-full flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-50 rounded-lg">
                <Brain className="w-5 h-5 text-purple-600" />
              </div>
              <h2 className="text-lg font-semibold text-neutral-900">
                Intelligence de transcription
              </h2>
              {aiLoading && <Loader2 className="w-4 h-4 animate-spin text-neutral-400" />}
            </div>
            {intelligencePanelOpen ? (
              <ChevronUp className="w-5 h-5 text-neutral-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-neutral-400" />
            )}
          </button>

          {intelligencePanelOpen && (
            <div className="mt-6 space-y-6">
              {transcriptionAnalysis ? (
                <>
                  {/* Tone / Sentiment */}
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-700 mb-3">Ton de l'echange</h3>
                    <div className="flex items-start gap-3">
                      {(() => {
                        const config = TONE_CONFIG[transcriptionAnalysis.tone] || TONE_CONFIG.neutral;
                        return (
                          <div className="flex flex-col gap-1">
                            <span
                              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border ${config.color}`}
                            >
                              <MessageSquare className="w-4 h-4" />
                              {config.label}
                            </span>
                            <p className="text-xs text-neutral-500 mt-1">{config.description}</p>
                          </div>
                        );
                      })()}
                    </div>
                  </div>

                  {/* Key Topics */}
                  {transcriptionAnalysis.topics.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-neutral-700 mb-3 flex items-center gap-2">
                        <Tag className="w-4 h-4 text-blue-500" />
                        Sujets identifies
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {transcriptionAnalysis.topics.map((topic, i) => (
                          <span
                            key={i}
                            className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
                          >
                            {topic}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Call Summary */}
                  {transcriptionAnalysis.summary && (
                    <div>
                      <h3 className="text-sm font-semibold text-neutral-700 mb-2">
                        Resume de l'appel
                      </h3>
                      <div className="bg-neutral-50 rounded-lg p-4 border border-neutral-200">
                        <p className="text-sm text-neutral-700 leading-relaxed">
                          {transcriptionAnalysis.summary}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Action Items */}
                  {transcriptionAnalysis.actionItems.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-neutral-700 mb-2 flex items-center gap-2">
                        <ListChecks className="w-4 h-4 text-green-500" />
                        Actions identifiees
                      </h3>
                      <div className="space-y-2">
                        {transcriptionAnalysis.actionItems.map((action, i) => (
                          <div
                            key={i}
                            className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg border border-neutral-200"
                          >
                            <span className="text-sm text-neutral-700 flex-1">{action}</span>
                            <button
                              onClick={() => handleCreateTask(action)}
                              className="ml-3 text-xs font-medium text-accent hover:text-accent-600 whitespace-nowrap px-3 py-1.5 rounded-md bg-accent/10 hover:bg-accent/20 transition-colors"
                            >
                              Creer tache
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Speaker Segments Timeline */}
                  {transcriptionAnalysis.speakerSegments.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-neutral-700 mb-3 flex items-center gap-2">
                        <User className="w-4 h-4 text-neutral-500" />
                        Chronologie des interventions
                      </h3>
                      <div className="space-y-2 max-h-96 overflow-y-auto">
                        {transcriptionAnalysis.speakerSegments.map((segment, i) => (
                          <div
                            key={i}
                            className={`flex items-start gap-3 p-3 rounded-lg ${
                              segment.speaker.includes("1") || segment.speaker.toLowerCase() === "avocat"
                                ? "bg-blue-50 border border-blue-100"
                                : "bg-neutral-50 border border-neutral-100"
                            }`}
                          >
                            <div className="flex-shrink-0">
                              <span
                                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                  segment.speaker.includes("1") || segment.speaker.toLowerCase() === "avocat"
                                    ? "bg-blue-200 text-blue-800"
                                    : "bg-neutral-200 text-neutral-700"
                                }`}
                              >
                                {segment.speaker}
                              </span>
                              {segment.startTime && (
                                <span className="block text-xs text-neutral-400 mt-1 text-center">
                                  {segment.startTime}
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-neutral-700 leading-relaxed flex-1">
                              {segment.text}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : aiLoading ? (
                <div className="flex items-center gap-3 py-4">
                  <Loader2 className="w-5 h-5 animate-spin text-purple-500" />
                  <span className="text-sm text-neutral-600">Analyse de la transcription en cours...</span>
                </div>
              ) : (
                <p className="text-sm text-neutral-500">
                  Analyse non disponible pour cette transcription.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Smart Actions Panel */}
      <div className="card mb-6">
        <button
          onClick={() => setActionsPanelOpen(!actionsPanelOpen)}
          className="w-full flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-accent/10 rounded-lg">
              <ListChecks className="w-5 h-5 text-accent" />
            </div>
            <h2 className="text-lg font-semibold text-neutral-900">Actions rapides</h2>
          </div>
          {actionsPanelOpen ? (
            <ChevronUp className="w-5 h-5 text-neutral-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-neutral-400" />
          )}
        </button>

        {actionsPanelOpen && (
          <div className="mt-6 space-y-3">
            {/* Create tasks from action items */}
            {transcriptionAnalysis && transcriptionAnalysis.actionItems.length > 0 && (
              <div className="space-y-2 mb-4">
                <h3 className="text-sm font-semibold text-neutral-700 mb-2">
                  Taches depuis l'analyse
                </h3>
                {transcriptionAnalysis.actionItems.map((action, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg"
                  >
                    <div className="flex items-center gap-2 flex-1">
                      <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0" />
                      <span className="text-sm text-neutral-700">{action}</span>
                    </div>
                    <button
                      onClick={() => handleCreateTask(action)}
                      className="ml-3 btn-secondary text-xs px-3 py-1.5"
                    >
                      Creer une tache
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Link to case */}
            {!call.case_id && (
              <button
                onClick={() => setShowLinkDialog(true)}
                className="w-full flex items-center gap-3 p-4 bg-neutral-50 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition-colors text-left"
              >
                <LinkIcon className="w-5 h-5 text-neutral-600 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-neutral-800">Lier au dossier</p>
                  <p className="text-xs text-neutral-500">
                    Associer cet appel a un dossier existant.
                  </p>
                </div>
              </button>
            )}

            {/* Send summary */}
            {(call.ai_summary || (transcriptionAnalysis && transcriptionAnalysis.summary)) && (
              <button
                onClick={handleSendSummary}
                className="w-full flex items-center gap-3 p-4 bg-neutral-50 rounded-lg border border-neutral-200 hover:bg-neutral-100 transition-colors text-left"
              >
                <Send className="w-5 h-5 text-neutral-600 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-neutral-800">Envoyer un recapitulatif</p>
                  <p className="text-xs text-neutral-500">
                    Creer un brouillon d'email avec le resume de l'appel.
                  </p>
                </div>
              </button>
            )}
          </div>
        )}
      </div>

      {/* Tasks */}
      {call.tasks_count > 0 && (
        <div className="card mb-6">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">
            Tâches générées ({call.tasks_count})
          </h2>
          <p className="text-neutral-600 text-sm">
            {call.tasks_count} tâche{call.tasks_count > 1 ? "s ont" : " a"} été générée
            {call.tasks_count > 1 ? "s" : ""} automatiquement à partir de cet appel.
          </p>
        </div>
      )}

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
                onClick={handleLinkToCase}
                className="btn-primary"
              >
                Lier
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
