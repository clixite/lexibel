"use client";

import { useState, useEffect } from "react";
import { X, ZoomIn, ZoomOut, ChevronLeft, ChevronRight, RotateCw, Download } from "lucide-react";
import { Document, Page, pdfjs } from "react-pdf";

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

interface DocumentPreviewProps {
  isOpen: boolean;
  onClose: () => void;
  fileId: string;
  fileName: string;
  mimeType: string;
  accessToken: string;
}

export default function DocumentPreview({
  isOpen,
  onClose,
  fileId,
  fileName,
  mimeType,
  accessToken,
}: DocumentPreviewProps) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [rotation, setRotation] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fileUrl, setFileUrl] = useState<string | null>(null);

  // Fetch file and create blob URL
  useEffect(() => {
    if (!isOpen || !fileId || !accessToken) return;

    const fetchFile = async () => {
      setLoading(true);
      setError(null);

      try {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
        const response = await fetch(`${apiBase}/documents/${fileId}/download`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        });

        if (!response.ok) {
          throw new Error(`Erreur ${response.status}: ${response.statusText}`);
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        setFileUrl(url);
      } catch (err) {
        console.error("Error fetching file:", err);
        setError(err instanceof Error ? err.message : "Erreur lors du chargement du fichier");
      } finally {
        setLoading(false);
      }
    };

    fetchFile();

    // Cleanup blob URL on unmount
    return () => {
      if (fileUrl) {
        URL.revokeObjectURL(fileUrl);
      }
    };
  }, [isOpen, fileId, accessToken]);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setPageNumber(1);
      setScale(1.0);
      setRotation(0);
      setLoading(true);
      setError(null);
    }
  }, [isOpen]);

  // Handle keyboard events
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case "Escape":
          onClose();
          break;
        case "ArrowLeft":
          if (numPages && pageNumber > 1) {
            setPageNumber(pageNumber - 1);
          }
          break;
        case "ArrowRight":
          if (numPages && pageNumber < numPages) {
            setPageNumber(pageNumber + 1);
          }
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, pageNumber, numPages]);

  if (!isOpen) return null;

  const isPDF = mimeType === "application/pdf" || fileName.toLowerCase().endsWith(".pdf");
  const isImage = mimeType.startsWith("image/");

  const handlePdfLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
  };

  const handlePdfLoadError = (error: Error) => {
    console.error("PDF load error:", error);
    setError("Erreur lors du chargement du PDF");
    setLoading(false);
  };

  const handleImageLoad = () => {
    setLoading(false);
  };

  const handleImageError = () => {
    setError("Erreur lors du chargement de l'image");
    setLoading(false);
  };

  const handleZoomIn = () => {
    setScale((prev) => Math.min(prev + 0.25, 3.0));
  };

  const handleZoomOut = () => {
    setScale((prev) => Math.max(prev - 0.25, 0.5));
  };

  const handleRotate = () => {
    setRotation((prev) => (prev + 90) % 360);
  };

  const handlePrevPage = () => {
    setPageNumber((prev) => Math.max(prev - 1, 1));
  };

  const handleNextPage = () => {
    setPageNumber((prev) => Math.min(prev + 1, numPages || 1));
  };

  const handleDownload = () => {
    if (!fileUrl) return;

    const link = document.createElement("a");
    link.href = fileUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-semibold text-neutral-900 truncate">
              {fileName}
            </h2>
            <p className="text-xs text-neutral-500 mt-0.5">{mimeType}</p>
          </div>
          <button
            onClick={onClose}
            className="ml-4 text-neutral-400 hover:text-neutral-600 transition-colors"
            aria-label="Fermer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6 bg-neutral-50 flex items-center justify-center">
          {loading && (
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
              <p className="text-sm text-neutral-500 mt-2">Chargement...</p>
            </div>
          )}

          {error && (
            <div className="text-center">
              <p className="text-danger-700 font-medium">{error}</p>
              <button
                onClick={handleDownload}
                className="mt-4 btn-secondary flex items-center gap-2 mx-auto"
              >
                <Download className="w-4 h-4" />
                Télécharger le fichier
              </button>
            </div>
          )}

          {!error && !loading && fileUrl && isPDF && (
            <div className="flex flex-col items-center">
              <Document
                file={fileUrl}
                onLoadSuccess={handlePdfLoadSuccess}
                onLoadError={handlePdfLoadError}
                loading=""
              >
                <Page
                  pageNumber={pageNumber}
                  scale={scale}
                  rotate={rotation}
                  loading=""
                  renderTextLayer={true}
                  renderAnnotationLayer={true}
                />
              </Document>
            </div>
          )}

          {!error && !loading && fileUrl && isImage && (
            <div className="flex items-center justify-center">
              <img
                src={fileUrl}
                alt={fileName}
                onLoad={handleImageLoad}
                onError={handleImageError}
                style={{
                  maxWidth: "100%",
                  maxHeight: "70vh",
                  transform: `scale(${scale}) rotate(${rotation}deg)`,
                  transition: "transform 0.2s ease",
                }}
                className="object-contain"
              />
            </div>
          )}

          {!error && !isPDF && !isImage && (
            <div className="text-center">
              <div className="bg-white rounded-lg p-8 shadow-subtle border border-neutral-200 max-w-md">
                <div className="w-16 h-16 mx-auto mb-4 bg-neutral-100 rounded-full flex items-center justify-center">
                  <Download className="w-8 h-8 text-neutral-400" />
                </div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-2">
                  Aperçu non disponible
                </h3>
                <p className="text-sm text-neutral-600 mb-1">
                  Type de fichier: {mimeType}
                </p>
                <p className="text-sm text-neutral-600 mb-4">
                  L'aperçu n'est disponible que pour les PDF et les images.
                </p>
                <button
                  onClick={handleDownload}
                  className="btn-primary flex items-center gap-2 mx-auto"
                >
                  <Download className="w-4 h-4" />
                  Télécharger le fichier
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Controls Toolbar */}
        {!error && (isPDF || isImage) && (
          <div className="border-t border-neutral-200 px-6 py-3 bg-white rounded-b-lg">
            <div className="flex items-center justify-between">
              {/* Left: Zoom controls */}
              <div className="flex items-center gap-2">
                <button
                  onClick={handleZoomOut}
                  disabled={scale <= 0.5}
                  className="p-2 rounded-md hover:bg-neutral-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  aria-label="Zoom arrière"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <span className="text-sm text-neutral-600 min-w-[60px] text-center">
                  {Math.round(scale * 100)}%
                </span>
                <button
                  onClick={handleZoomIn}
                  disabled={scale >= 3.0}
                  className="p-2 rounded-md hover:bg-neutral-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  aria-label="Zoom avant"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
                <div className="h-6 w-px bg-neutral-200 mx-2"></div>
                <button
                  onClick={handleRotate}
                  className="p-2 rounded-md hover:bg-neutral-100 transition-colors"
                  aria-label="Rotation"
                >
                  <RotateCw className="w-4 h-4" />
                </button>
              </div>

              {/* Center: Page navigation (PDF only) */}
              {isPDF && numPages && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={handlePrevPage}
                    disabled={pageNumber <= 1}
                    className="p-2 rounded-md hover:bg-neutral-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    aria-label="Page précédente"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="text-sm text-neutral-700 min-w-[100px] text-center">
                    Page {pageNumber} / {numPages}
                  </span>
                  <button
                    onClick={handleNextPage}
                    disabled={pageNumber >= numPages}
                    className="p-2 rounded-md hover:bg-neutral-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    aria-label="Page suivante"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              )}

              {/* Right: Download button */}
              <button
                onClick={handleDownload}
                className="btn-secondary flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Télécharger
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
