"use client";

import { useSession } from "next-auth/react";
import { useState, useRef } from "react";
import {
  Upload,
  FileAudio,
  Clock,
  User,
  Search,
  Download,
  Loader2,
  Check,
  X,
  Play,
  Pause,
  AlertCircle,
  Filter,
  ChevronDown,
} from "lucide-react";
import { useTranscriptions } from "@/lib/hooks/useTranscriptions";
import { useUploadTranscription } from "@/lib/hooks/useUploadTranscription";
import { toast } from "sonner";
import type { Transcription, SearchTranscriptionsParams } from "@/lib/types/transcription";

const STATUS_LABELS = {
  pending: "En attente",
  processing: "En cours",
  completed: "Terminé",
  failed: "Échoué",
};

const STATUS_COLORS = {
  pending: "bg-neutral-100 text-neutral-600",
  processing: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

const LANGUAGES = [
  { value: "fr", label: "Français" },
  { value: "nl", label: "Néerlandais" },
  { value: "en", label: "Anglais" },
  { value: "de", label: "Allemand" },
];

export default function TranscriptionPage() {
  const { data: session } = useSession();
  const user = session?.user as any;
  const token = user?.accessToken;
  const tenantId = user?.tenantId;

  const [searchParams, setSearchParams] = useState<SearchTranscriptionsParams>({
    limit: 20,
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedTranscription, setSelectedTranscription] = useState<Transcription | null>(null);

  // Upload state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadLanguage, setUploadLanguage] = useState("fr");
  const [uploadDetectSpeakers, setUploadDetectSpeakers] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Hooks
  const transcriptionsQuery = useTranscriptions(searchParams, token, tenantId);
  const uploadMutation = useUploadTranscription({
    token,
    tenantId,
    onSuccess: (response) => {
      toast.success("Transcription démarrée", {
        description: "Le fichier audio est en cours de traitement.",
      });
      setShowUploadModal(false);
      setUploadFile(null);
    },
    onError: (error) => {
      toast.error("Erreur d'upload", {
        description: error.message,
      });
    },
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const validTypes = ["audio/mpeg", "audio/mp3", "audio/wav", "audio/m4a", "audio/ogg"];
    if (!validTypes.includes(file.type) && !file.name.match(/\.(mp3|wav|m4a|ogg)$/i)) {
      toast.error("Type de fichier non valide", {
        description: "Veuillez sélectionner un fichier audio (MP3, WAV, M4A, OGG).",
      });
      return;
    }

    // Validate file size (max 100MB)
    if (file.size > 100 * 1024 * 1024) {
      toast.error("Fichier trop volumineux", {
        description: "La taille maximale est de 100 MB.",
      });
      return;
    }

    setUploadFile(file);
  };

  const handleUpload = () => {
    if (!uploadFile) return;

    uploadMutation.mutate({
      file: uploadFile,
      language: uploadLanguage,
      detect_speakers: uploadDetectSpeakers,
    });
  };

  const handleSearch = () => {
    setSearchParams((prev) => ({ ...prev, query: searchQuery }));
  };

  const handleDownloadTranscript = (transcription: Transcription) => {
    const blob = new Blob([transcription.full_text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${transcription.file_name.replace(/\.[^.]+$/, "")}_transcript.txt`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Transcription téléchargée");
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Transcriptions Audio</h1>
          <p className="text-neutral-500 text-sm mt-1">
            Transcription automatique avec détection des locuteurs
          </p>
        </div>
        <button
          onClick={() => setShowUploadModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Upload className="w-4 h-4" />
          Uploader un audio
        </button>
      </div>

      {/* Search and filters */}
      <div className="flex items-center gap-3 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
          <input
            type="text"
            placeholder="Rechercher dans les transcriptions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSearch()}
            className="input pl-9"
          />
        </div>
        <select
          className="px-4 py-2 border border-neutral-200 rounded-lg text-sm"
          onChange={(e) =>
            setSearchParams((prev) => ({ ...prev, status: e.target.value || undefined }))
          }
        >
          <option value="">Tous les statuts</option>
          <option value="completed">Terminés</option>
          <option value="processing">En cours</option>
          <option value="pending">En attente</option>
          <option value="failed">Échoués</option>
        </select>
        <select
          className="px-4 py-2 border border-neutral-200 rounded-lg text-sm"
          onChange={(e) =>
            setSearchParams((prev) => ({ ...prev, language: e.target.value || undefined }))
          }
        >
          <option value="">Toutes les langues</option>
          {LANGUAGES.map((lang) => (
            <option key={lang.value} value={lang.value}>
              {lang.label}
            </option>
          ))}
        </select>
      </div>

      {/* Transcriptions list */}
      {transcriptionsQuery.isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
        </div>
      )}

      {transcriptionsQuery.isError && (
        <div className="bg-red-50 rounded-lg p-6 border border-red-200">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-6 w-6 text-red-600" />
            <div>
              <h3 className="font-semibold text-red-900">Erreur de chargement</h3>
              <p className="text-sm text-red-700 mt-1">
                Impossible de charger les transcriptions. Veuillez réessayer.
              </p>
            </div>
          </div>
        </div>
      )}

      {transcriptionsQuery.data && transcriptionsQuery.data.items.length === 0 && (
        <div className="bg-white rounded-lg p-12 text-center border border-neutral-200">
          <FileAudio className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-neutral-600 mb-2">
            Aucune transcription
          </h3>
          <p className="text-neutral-500 mb-6">
            {searchQuery || searchParams.status
              ? "Essayez de modifier vos filtres."
              : "Uploadez votre premier fichier audio pour commencer."}
          </p>
          {!searchQuery && !searchParams.status && (
            <button
              onClick={() => setShowUploadModal(true)}
              className="btn-primary"
            >
              <Upload className="w-4 h-4 inline mr-2" />
              Uploader un audio
            </button>
          )}
        </div>
      )}

      {transcriptionsQuery.data && transcriptionsQuery.data.items.length > 0 && (
        <div className="space-y-4">
          {transcriptionsQuery.data.items.map((transcription) => (
            <div
              key={transcription.id}
              className="card hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => setSelectedTranscription(transcription)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4 flex-1">
                  <div className="p-3 bg-accent-50 rounded-lg">
                    <FileAudio className="w-6 h-6 text-accent-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-neutral-900 truncate">
                        {transcription.file_name}
                      </h3>
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          STATUS_COLORS[transcription.status]
                        }`}
                      >
                        {STATUS_LABELS[transcription.status]}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-neutral-500">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {formatDuration(transcription.duration_seconds)}
                      </span>
                      <span className="flex items-center gap-1">
                        <User className="w-3.5 h-3.5" />
                        {transcription.speakers_detected} locuteurs
                      </span>
                      <span>{formatFileSize(transcription.file_size)}</span>
                      <span>{LANGUAGES.find((l) => l.value === transcription.language)?.label}</span>
                    </div>
                    {transcription.status === "completed" && (
                      <p className="text-sm text-neutral-600 mt-2 line-clamp-2">
                        {transcription.full_text}
                      </p>
                    )}
                    {transcription.status === "failed" && transcription.error_message && (
                      <p className="text-sm text-red-600 mt-2">
                        Erreur: {transcription.error_message}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {transcription.status === "completed" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDownloadTranscript(transcription);
                      }}
                      className="p-2 hover:bg-neutral-100 rounded-md transition-colors"
                      title="Télécharger"
                    >
                      <Download className="w-4 h-4 text-neutral-600" />
                    </button>
                  )}
                  {transcription.status === "processing" && (
                    <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-neutral-900">
                Uploader un fichier audio
              </h2>
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setUploadFile(null);
                }}
                className="text-neutral-400 hover:text-neutral-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {/* File input */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Fichier audio
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="audio/*,.mp3,.wav,.m4a,.ogg"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full border-2 border-dashed border-neutral-300 rounded-lg p-8 hover:border-accent-400 hover:bg-accent-50/50 transition-colors"
                >
                  {uploadFile ? (
                    <div className="flex items-center justify-center gap-3">
                      <FileAudio className="w-8 h-8 text-accent-600" />
                      <div className="text-left">
                        <p className="font-medium text-neutral-900">{uploadFile.name}</p>
                        <p className="text-sm text-neutral-500">
                          {formatFileSize(uploadFile.size)}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <Upload className="w-12 h-12 text-neutral-400 mx-auto mb-2" />
                      <p className="text-neutral-600 font-medium">
                        Cliquez pour sélectionner un fichier
                      </p>
                      <p className="text-sm text-neutral-500 mt-1">
                        MP3, WAV, M4A, OGG (max 100 MB)
                      </p>
                    </div>
                  )}
                </button>
              </div>

              {/* Language select */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Langue de l'audio
                </label>
                <select
                  value={uploadLanguage}
                  onChange={(e) => setUploadLanguage(e.target.value)}
                  className="input"
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang.value} value={lang.value}>
                      {lang.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Speaker detection */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={uploadDetectSpeakers}
                  onChange={(e) => setUploadDetectSpeakers(e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm text-neutral-700">
                  Détecter automatiquement les locuteurs
                </span>
              </label>

              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => {
                    setShowUploadModal(false);
                    setUploadFile(null);
                  }}
                  className="btn-secondary flex-1"
                >
                  Annuler
                </button>
                <button
                  onClick={handleUpload}
                  disabled={!uploadFile || uploadMutation.isPending}
                  className="btn-primary flex-1 flex items-center justify-center gap-2"
                >
                  {uploadMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  {uploadMutation.isPending ? "Upload en cours..." : "Démarrer la transcription"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {selectedTranscription && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-neutral-200">
              <div className="flex-1 min-w-0">
                <h2 className="text-lg font-semibold text-neutral-900 truncate">
                  {selectedTranscription.file_name}
                </h2>
                <div className="flex items-center gap-4 text-sm text-neutral-500 mt-1">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {formatDuration(selectedTranscription.duration_seconds)}
                  </span>
                  <span className="flex items-center gap-1">
                    <User className="w-3.5 h-3.5" />
                    {selectedTranscription.speakers_detected} locuteurs
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      STATUS_COLORS[selectedTranscription.status]
                    }`}
                  >
                    {STATUS_LABELS[selectedTranscription.status]}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedTranscription(null)}
                className="text-neutral-400 hover:text-neutral-600 ml-4"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {selectedTranscription.status === "completed" && (
                <div className="space-y-6">
                  {/* Full transcript */}
                  <div>
                    <h3 className="font-semibold text-neutral-900 mb-3">
                      Transcription complète
                    </h3>
                    <div className="bg-neutral-50 rounded-lg p-4 border border-neutral-200">
                      <p className="text-neutral-700 leading-relaxed whitespace-pre-wrap">
                        {selectedTranscription.full_text}
                      </p>
                    </div>
                  </div>

                  {/* Segments */}
                  {selectedTranscription.segments.length > 0 && (
                    <div>
                      <h3 className="font-semibold text-neutral-900 mb-3">
                        Segments ({selectedTranscription.segments.length})
                      </h3>
                      <div className="space-y-2">
                        {selectedTranscription.segments.map((segment, idx) => (
                          <div
                            key={idx}
                            className="flex gap-4 p-3 bg-white rounded-lg border border-neutral-200"
                          >
                            <div className="text-xs text-neutral-500 font-mono w-24 flex-shrink-0">
                              {formatDuration(segment.start)} - {formatDuration(segment.end)}
                            </div>
                            <div className="flex-1">
                              {segment.speaker && (
                                <span className="text-xs font-medium text-accent-600 mr-2">
                                  {segment.speaker}:
                                </span>
                              )}
                              <span className="text-sm text-neutral-700">{segment.text}</span>
                            </div>
                            <div className="text-xs text-neutral-400">
                              {Math.round(segment.confidence * 100)}%
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {selectedTranscription.status === "processing" && (
                <div className="text-center py-12">
                  <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
                  <p className="text-neutral-600 font-medium">Transcription en cours...</p>
                  <p className="text-sm text-neutral-500 mt-1">
                    Cela peut prendre quelques minutes selon la durée de l'audio.
                  </p>
                </div>
              )}

              {selectedTranscription.status === "pending" && (
                <div className="text-center py-12">
                  <Clock className="w-12 h-12 text-neutral-400 mx-auto mb-4" />
                  <p className="text-neutral-600 font-medium">En attente de traitement</p>
                </div>
              )}

              {selectedTranscription.status === "failed" && (
                <div className="text-center py-12">
                  <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                  <p className="text-neutral-600 font-medium">Échec de la transcription</p>
                  {selectedTranscription.error_message && (
                    <p className="text-sm text-red-600 mt-2">
                      {selectedTranscription.error_message}
                    </p>
                  )}
                </div>
              )}
            </div>

            {selectedTranscription.status === "completed" && (
              <div className="p-6 border-t border-neutral-200">
                <button
                  onClick={() => handleDownloadTranscript(selectedTranscription)}
                  className="btn-primary w-full flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Télécharger la transcription
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
