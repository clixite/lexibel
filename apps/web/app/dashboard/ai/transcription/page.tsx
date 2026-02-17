"use client";

import { useSession } from "next-auth/react";
import { useState, useRef, useEffect } from "react";
import {
  Upload,
  FileAudio,
  Clock,
  User,
  Download,
  Loader2,
  X,
  AlertCircle,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, EmptyState, DataTable, Badge } from "@/components/ui";
import { toast } from "sonner";

interface Transcription {
  id: string;
  created_at: string;
  source: "PLAUD" | "RINGOVER" | "UPLOAD";
  duration: number;
  status: "pending" | "processing" | "completed" | "failed";
  full_text?: string;
  segments: Array<{
    timestamp: string;
    speaker?: string;
    text: string;
  }>;
}

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

export default function TranscriptionPage() {
  const { data: session } = useSession();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedTranscription, setSelectedTranscription] = useState<Transcription | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        setError("");
        const res = await apiFetch<Transcription[]>("/transcriptions", session?.user?.accessToken);
        setTranscriptions(Array.isArray(res) ? res : res.items || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur de chargement");
      } finally {
        setLoading(false);
      }
    }

    if (session?.user?.accessToken) {
      fetchData();
    }
  }, [session?.user?.accessToken]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const validTypes = ["audio/mpeg", "audio/mp3", "audio/wav", "audio/m4a", "audio/ogg"];
    if (!validTypes.includes(file.type) && !file.name.match(/\.(mp3|wav|m4a|ogg)$/i)) {
      toast.error("Type de fichier non valide", {
        description: "Veuillez sélectionner un fichier audio (MP3, WAV, M4A, OGG).",
      });
      return;
    }

    if (file.size > 100 * 1024 * 1024) {
      toast.error("Fichier trop volumineux", {
        description: "La taille maximale est de 100 MB.",
      });
      return;
    }

    setUploadFile(file);
  };

  const handleUpload = async () => {
    if (!uploadFile) return;

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append("file", uploadFile);

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/transcriptions/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session?.user?.accessToken}`,
        },
        body: formData,
      });

      if (!response.ok) throw new Error("Upload failed");

      toast.success("Transcription démarrée", {
        description: "Le fichier audio est en cours de traitement.",
      });
      setShowUploadModal(false);
      setUploadFile(null);

      // Reload data
      const res = await apiFetch<Transcription[]>("/transcriptions", session?.user?.accessToken);
      setTranscriptions(Array.isArray(res) ? res : res.items || []);
    } catch (err) {
      toast.error("Erreur d'upload", {
        description: err instanceof Error ? err.message : "Impossible d'uploader le fichier",
      });
    } finally {
      setUploading(false);
    }
  };

  const handleDownloadTranscript = (transcription: Transcription) => {
    if (!transcription.full_text) return;
    const blob = new Blob([transcription.full_text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `transcription_${transcription.id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Transcription téléchargée");
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div>
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

      {loading && <LoadingSkeleton />}

      {error && <ErrorState title="Erreur de chargement" description={error} />}

      {!loading && transcriptions.length === 0 && (
        <EmptyState
          icon={<FileAudio className="w-12 h-12" />}
          title="Aucune transcription"
          description="Uploadez votre premier fichier audio pour commencer"
        />
      )}

      {!loading && transcriptions.length > 0 && (
        <DataTable
          data={transcriptions}
          columns={[
            {
              key: "created_at",
              label: "Date",
              render: (trans) => new Date(trans.created_at).toLocaleDateString("fr-FR"),
            },
            {
              key: "source",
              label: "Source",
              render: (trans) => <span>{trans.source}</span>,
            },
            {
              key: "duration",
              label: "Durée",
              render: (trans) => formatDuration(trans.duration),
            },
            {
              key: "status",
              label: "Statut",
              render: (trans) => (
                <Badge variant="default">
                  {STATUS_LABELS[trans.status]}
                </Badge>
              ),
            },
            {
              key: "actions",
              label: "Actions",
              render: (trans) => (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedTranscription(trans)}
                    className="text-accent hover:text-accent-600 text-sm"
                  >
                    Voir
                  </button>
                  {trans.status === "completed" && (
                    <button
                      onClick={() => handleDownloadTranscript(trans)}
                      className="text-neutral-600 hover:text-neutral-900"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ),
            },
          ]}
          onRowClick={(trans) => setSelectedTranscription(trans)}
        />
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
                          {(uploadFile.size / (1024 * 1024)).toFixed(1)} MB
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
                  disabled={!uploadFile || uploading}
                  className="btn-primary flex-1 flex items-center justify-center gap-2"
                >
                  {uploading && <Loader2 className="w-4 h-4 animate-spin" />}
                  {uploading ? "Upload en cours..." : "Démarrer la transcription"}
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
                  Transcription {selectedTranscription.id}
                </h2>
                <div className="flex items-center gap-4 text-sm text-neutral-500 mt-1">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {formatDuration(selectedTranscription.duration)}
                  </span>
                  <span className="flex items-center gap-1">
                    <User className="w-3.5 h-3.5" />
                    {selectedTranscription.source}
                  </span>
                  <Badge variant="default">
                    {STATUS_LABELS[selectedTranscription.status]}
                  </Badge>
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
                  {selectedTranscription.full_text && (
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
                  )}

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
                              {segment.timestamp}
                            </div>
                            <div className="flex-1">
                              {segment.speaker && (
                                <span className="text-xs font-medium text-accent-600 mr-2">
                                  {segment.speaker}:
                                </span>
                              )}
                              <span className="text-sm text-neutral-700">{segment.text}</span>
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
                </div>
              )}
            </div>

            {selectedTranscription.status === "completed" && selectedTranscription.full_text && (
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
