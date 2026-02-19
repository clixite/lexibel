"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/lib/useAuth";
import {
  FolderOpen,
  File,
  FileText,
  FileSpreadsheet,
  Presentation,
  Image,
  Search,
  RefreshCw,
  Link2,
  ExternalLink,
  Edit3,
  ChevronRight,
  Home,
  Filter,
  Grid,
  List,
  Cloud,
  Loader2,
  X,
  AlertCircle,
  CheckCircle2,
  Download,
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface CloudDocument {
  id: string;
  oauth_token_id: string;
  case_id: string | null;
  provider: string;
  external_id: string;
  name: string;
  mime_type: string | null;
  size_bytes: number | null;
  web_url: string | null;
  edit_url: string | null;
  thumbnail_url: string | null;
  is_folder: boolean;
  path: string | null;
  last_modified_at: string | null;
  last_modified_by: string | null;
  is_indexed: boolean;
  index_status: string;
  created_at: string;
  updated_at: string;
}

interface Connection {
  id: string;
  provider: string;
  email_address: string | null;
  status: string;
}

interface BreadcrumbItem {
  name: string;
  folderId: string | null;
}

function formatBytes(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("fr-BE", { day: "2-digit", month: "short", year: "numeric" });
}

function getFileIcon(doc: CloudDocument) {
  if (doc.is_folder) {
    return <FolderOpen className="w-5 h-5 text-yellow-500" />;
  }
  const mime = doc.mime_type || "";
  const name = doc.name.toLowerCase();

  if (mime.includes("pdf") || name.endsWith(".pdf")) {
    return <FileText className="w-5 h-5 text-red-500" />;
  }
  if (
    mime.includes("spreadsheet") ||
    mime.includes("sheet") ||
    name.endsWith(".xlsx") ||
    name.endsWith(".ods")
  ) {
    return <FileSpreadsheet className="w-5 h-5 text-green-600" />;
  }
  if (
    mime.includes("presentation") ||
    mime.includes("slides") ||
    name.endsWith(".pptx") ||
    name.endsWith(".odp")
  ) {
    return <Presentation className="w-5 h-5 text-orange-500" />;
  }
  if (mime.includes("word") || mime.includes("document") || name.endsWith(".docx")) {
    return <FileText className="w-5 h-5 text-blue-500" />;
  }
  if (mime.includes("image")) {
    return <Image className="w-5 h-5 text-purple-500" />;
  }
  return <File className="w-5 h-5 text-gray-400" />;
}

function ProviderBadge({ provider }: { provider: string }) {
  if (provider === "google_drive") {
    return (
      <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium">
        Drive
      </span>
    );
  }
  if (provider === "onedrive") {
    return (
      <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-100 text-sky-700 font-medium">
        OneDrive
      </span>
    );
  }
  if (provider === "sharepoint") {
    return (
      <span className="text-[10px] px-1.5 py-0.5 rounded bg-teal-100 text-teal-700 font-medium">
        SharePoint
      </span>
    );
  }
  return null;
}

interface LinkCaseModalProps {
  document: CloudDocument;
  token: string;
  tenantId: string;
  onClose: () => void;
  onLinked: () => void;
}

function LinkCaseModal({ document, token, tenantId, onClose, onLinked }: LinkCaseModalProps) {
  const [cases, setCases] = useState<Array<{ id: string; reference: string; title: string }>>([]);
  const [selectedCase, setSelectedCase] = useState("");
  const [linkType, setLinkType] = useState("reference");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<{ cases: Array<{ id: string; reference: string; title: string }> }>(
      "/cases?per_page=50",
      token,
      { tenantId }
    )
      .then((res) => setCases(res.cases || []))
      .catch(() => {});
  }, [token, tenantId]);

  const handleLink = async () => {
    if (!selectedCase) return;
    setLoading(true);
    setError("");
    try {
      await apiFetch(`/cloud-documents/${document.id}/link-case`, token, {
        method: "POST",
        tenantId,
        body: JSON.stringify({ case_id: selectedCase, link_type: linkType }),
      });
      onLinked();
      onClose();
    } catch (e: any) {
      setError(e.message || "Erreur lors de la liaison");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900">Lier à un dossier</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-sm text-gray-500 mb-4 truncate">
          {document.name}
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Dossier juridique
            </label>
            <select
              value={selectedCase}
              onChange={(e) => setSelectedCase(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="">Sélectionner un dossier...</option>
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.reference} — {c.title}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type de lien
            </label>
            <select
              value={linkType}
              onChange={(e) => setLinkType(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="reference">Référence</option>
              <option value="evidence">Pièce à conviction</option>
              <option value="contract">Contrat</option>
              <option value="correspondence">Correspondance</option>
              <option value="other">Autre</option>
            </select>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm hover:bg-gray-50"
            >
              Annuler
            </button>
            <button
              onClick={handleLink}
              disabled={!selectedCase || loading}
              className="flex-1 px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90 disabled:opacity-50"
            >
              {loading ? "Liaison..." : "Lier"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DocumentsPage() {
  const { accessToken, tenantId } = useAuth();

  const [documents, setDocuments] = useState<CloudDocument[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedConnection, setSelectedConnection] = useState<string>("");
  const [selectedProvider, setSelectedProvider] = useState<string>("");
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [breadcrumb, setBreadcrumb] = useState<BreadcrumbItem[]>([
    { name: "Racine", folderId: null },
  ]);
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [linkingDoc, setLinkingDoc] = useState<CloudDocument | null>(null);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    if (!accessToken) return;
    apiFetch<Connection[]>("/oauth/tokens", accessToken, { tenantId })
      .then((data) => setConnections(data || []))
      .catch(() => {});
  }, [accessToken, tenantId]);

  const loadDocuments = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        per_page: "50",
      });
      if (selectedConnection) params.set("connection_id", selectedConnection);
      if (selectedProvider) params.set("provider", selectedProvider);
      if (currentFolderId) params.set("folder_id", currentFolderId);
      if (searchQuery) params.set("search", searchQuery);

      const res = await apiFetch<{ documents: CloudDocument[]; total: number }>(
        `/cloud-documents?${params.toString()}`,
        accessToken,
        { tenantId }
      );
      setDocuments(res.documents || []);
      setTotal(res.total || 0);
    } catch (e) {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, [accessToken, tenantId, page, selectedConnection, selectedProvider, currentFolderId, searchQuery]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleFolderClick = (doc: CloudDocument) => {
    if (!doc.is_folder) return;
    setCurrentFolderId(doc.external_id);
    setBreadcrumb((prev) => [...prev, { name: doc.name, folderId: doc.external_id }]);
    setPage(1);
  };

  const handleBreadcrumbClick = (item: BreadcrumbItem, index: number) => {
    setCurrentFolderId(item.folderId);
    setBreadcrumb((prev) => prev.slice(0, index + 1));
    setPage(1);
  };

  const handleSync = async (connectionId: string) => {
    setSyncing(true);
    try {
      await apiFetch("/sync", accessToken, {
        method: "POST",
        tenantId,
        body: JSON.stringify({ connection_id: connectionId, job_type: "incremental" }),
      });
      setTimeout(loadDocuments, 2000);
    } catch (e) {
      // Sync failed silently
    } finally {
      setSyncing(false);
    }
  };
  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-8 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Documents Cloud</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {total} document{total !== 1 ? "s" : ""} synchronisé{total !== 1 ? "s" : ""}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {selectedConnection && (
              <button
                onClick={() => handleSync(selectedConnection)}
                disabled={syncing}
                className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />
                Synchroniser
              </button>
            )}
            <div className="flex border border-gray-200 rounded-lg overflow-hidden">
              <button
                onClick={() => setViewMode("list")}
                className={`px-3 py-2 ${viewMode === "list" ? "bg-gray-100" : ""}`}
              >
                <List className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode("grid")}
                className={`px-3 py-2 ${viewMode === "grid" ? "bg-gray-100" : ""}`}
              >
                <Grid className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>


        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 mt-4">
          <div className="relative flex-1 min-w-[200px] max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              placeholder="Rechercher un document..."
              className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>

          <select
            value={selectedConnection}
            onChange={(e) => {
              setSelectedConnection(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="">Toutes les connexions</option>
            {connections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.email_address || c.provider} ({c.provider === "google" ? "Google" : "Microsoft"})
              </option>
            ))}
          </select>

          <select
            value={selectedProvider}
            onChange={(e) => {
              setSelectedProvider(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="">Tous les providers</option>
            <option value="google_drive">Google Drive</option>
            <option value="onedrive">OneDrive</option>
            <option value="sharepoint">SharePoint</option>
          </select>
        </div>

        {/* Breadcrumb */}
        <div className="flex items-center gap-1 mt-3 text-sm text-gray-500">
          <Home className="w-3.5 h-3.5" />
          {breadcrumb.map((item, index) => (
            <span key={index} className="flex items-center gap-1">
              <ChevronRight className="w-3.5 h-3.5" />
              <button
                onClick={() => handleBreadcrumbClick(item, index)}
                className={`hover:text-accent ${
                  index === breadcrumb.length - 1 ? "font-medium text-gray-900" : ""
                }`}
              >
                {item.name}
              </button>
            </span>
          ))}
        </div>
      </div>


      {/* Content */}
      <div className="p-8">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-accent" />
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-20">
            <Cloud className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 font-medium">Aucun document trouvé</p>
            <p className="text-sm text-gray-400 mt-1">
              Connectez un compte Google ou Microsoft et lancez une synchronisation
            </p>
          </div>
        ) : viewMode === "list" ? (

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Nom</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 hidden md:table-cell">
                    Taille
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 hidden lg:table-cell">
                    Modifié
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 hidden lg:table-cell">
                    Provider
                  </th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr
                    key={doc.id}
                    className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                  >

                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        {getFileIcon(doc)}
                        <div>
                          <button
                            onClick={() => doc.is_folder && handleFolderClick(doc)}
                            className={`font-medium text-gray-900 text-left ${
                              doc.is_folder ? "hover:text-accent cursor-pointer" : ""
                            }`}
                          >
                            {doc.name}
                          </button>
                          {doc.path && (
                            <p className="text-[11px] text-gray-400 truncate max-w-xs">
                              {doc.path}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-500 hidden md:table-cell">
                      {formatBytes(doc.size_bytes)}
                    </td>
                    <td className="px-4 py-3 text-gray-500 hidden lg:table-cell">
                      {formatDate(doc.last_modified_at)}
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <ProviderBadge provider={doc.provider} />
                    </td>

                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        {doc.web_url && !doc.is_folder && (
                          <a
                            href={doc.web_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            title="Ouvrir"
                            className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-accent"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        )}
                        {doc.edit_url && !doc.is_folder && (
                          <a
                            href={doc.edit_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            title="Éditer en ligne"
                            className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-green-600"
                          >
                            <Edit3 className="w-4 h-4" />
                          </a>
                        )}
                        {!doc.is_folder && (
                          <button
                            onClick={() => setLinkingDoc(doc)}
                            title="Lier à un dossier"
                            className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-blue-600"
                          >
                            <Link2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md transition-shadow group cursor-pointer"
                onClick={() => doc.is_folder && handleFolderClick(doc)}
              >
                <div className="flex flex-col items-center text-center gap-3">
                  <div className="w-12 h-12 flex items-center justify-center">
                    {doc.is_folder ? (
                      <FolderOpen className="w-10 h-10 text-yellow-500" />
                    ) : (
                      <div className="scale-150">{getFileIcon(doc)}</div>
                    )}
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-900 truncate w-full max-w-[100px]">
                      {doc.name}
                    </p>
                    <p className="text-[10px] text-gray-400 mt-0.5">
                      {formatBytes(doc.size_bytes)}
                    </p>
                  </div>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {doc.web_url && (
                      <a
                        href={doc.web_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="p-1 rounded hover:bg-gray-100 text-gray-400"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                    {!doc.is_folder && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setLinkingDoc(doc);
                        }}
                        className="p-1 rounded hover:bg-gray-100 text-gray-400"
                      >
                        <Link2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}


        {total > 50 && (
          <div className="flex items-center justify-center gap-3 mt-6">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 border border-gray-200 rounded-lg text-sm disabled:opacity-50 hover:bg-gray-50"
            >
              Précédent
            </button>
            <span className="text-sm text-gray-500">
              Page {page} / {Math.ceil(total / 50)}
            </span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= Math.ceil(total / 50)}
              className="px-4 py-2 border border-gray-200 rounded-lg text-sm disabled:opacity-50 hover:bg-gray-50"
            >
              Suivant
            </button>
          </div>
        )}
      </div>

      {linkingDoc && (
        <LinkCaseModal
          document={linkingDoc}
          token={accessToken}
          tenantId={tenantId}
          onClose={() => setLinkingDoc(null)}
          onLinked={loadDocuments}
        />
      )}
    </div>
  );
}