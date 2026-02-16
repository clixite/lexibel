"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { Plus, ChevronDown, ChevronRight, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface InvoiceLine {
  id: string;
  description: string;
  quantity: number;
  unit_price_cents: number;
  total_cents: number;
}

interface Invoice {
  id: string;
  invoice_number: string;
  case_id: string;
  subtotal_cents: number;
  vat_cents: number;
  total_cents: number;
  status: string;
  peppol_status: string | null;
  created_at: string;
  lines?: InvoiceLine[];
}

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  approved: "bg-blue-100 text-blue-700",
  sent: "bg-amber-100 text-amber-700",
  paid: "bg-green-100 text-green-700",
  overdue: "bg-red-100 text-red-700",
  cancelled: "bg-red-50 text-red-500",
};

const PEPPOL_COLORS: Record<string, string> = {
  pending: "bg-amber-50 text-amber-600",
  sent: "bg-blue-50 text-blue-600",
  delivered: "bg-green-50 text-green-600",
  failed: "bg-red-50 text-red-600",
};

function formatCents(cents: number): string {
  return (cents / 100).toFixed(2) + " €";
}

export default function InvoiceList() {
  const { data: session } = useSession();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loadingLines, setLoadingLines] = useState<string | null>(null);

  const token = (session?.user as any)?.accessToken;

  useEffect(() => {
    if (!token) return;
    apiFetch<{ items: Invoice[] }>("/invoices", token)
      .then((data) => setInvoices(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  const toggleExpand = async (invoice: Invoice) => {
    if (expandedId === invoice.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(invoice.id);
    if (!invoice.lines && token) {
      setLoadingLines(invoice.id);
      try {
        const detail = await apiFetch<Invoice>(`/invoices/${invoice.id}`, token);
        setInvoices((prev) =>
          prev.map((inv) => (inv.id === invoice.id ? { ...inv, lines: detail.lines } : inv))
        );
      } catch {
        // Silently fail — lines just won't show
      } finally {
        setLoadingLines(null);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div />
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
          <Plus className="w-4 h-4" />
          Créer facture
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="w-8 px-3 py-3"></th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Numéro</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">HT</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">TVA</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">TTC</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Peppol</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {invoices.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-sm text-gray-400">
                  Aucune facture trouvée.
                </td>
              </tr>
            ) : (
              invoices.map((inv) => (
                <>
                  <tr
                    key={inv.id}
                    onClick={() => toggleExpand(inv)}
                    className="hover:bg-gray-50 transition-colors cursor-pointer"
                  >
                    <td className="px-3 py-4 text-gray-400">
                      {expandedId === inv.id ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-blue-600">{inv.invoice_number}</td>
                    <td className="px-6 py-4 text-sm text-gray-900">{formatCents(inv.subtotal_cents)}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{formatCents(inv.vat_cents)}</td>
                    <td className="px-6 py-4 text-sm font-semibold text-gray-900">{formatCents(inv.total_cents)}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[inv.status] || "bg-gray-100 text-gray-700"}`}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {inv.peppol_status && (
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${PEPPOL_COLORS[inv.peppol_status] || "bg-gray-100 text-gray-600"}`}>
                          {inv.peppol_status}
                        </span>
                      )}
                    </td>
                  </tr>
                  {expandedId === inv.id && (
                    <tr key={`${inv.id}-lines`}>
                      <td colSpan={7} className="px-10 py-4 bg-gray-50">
                        {loadingLines === inv.id ? (
                          <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                        ) : inv.lines && inv.lines.length > 0 ? (
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="text-xs text-gray-500 uppercase">
                                <th className="text-left py-1">Description</th>
                                <th className="text-right py-1">Qté</th>
                                <th className="text-right py-1">PU</th>
                                <th className="text-right py-1">Total</th>
                              </tr>
                            </thead>
                            <tbody>
                              {inv.lines.map((line) => (
                                <tr key={line.id} className="border-t border-gray-200">
                                  <td className="py-2 text-gray-700">{line.description}</td>
                                  <td className="py-2 text-right text-gray-500">{line.quantity}</td>
                                  <td className="py-2 text-right text-gray-500">{formatCents(line.unit_price_cents)}</td>
                                  <td className="py-2 text-right font-medium text-gray-900">{formatCents(line.total_cents)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : (
                          <p className="text-gray-400 text-sm">Aucune ligne.</p>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
