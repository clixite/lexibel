"use client";

import { useSession } from "next-auth/react";
import { Fragment, useEffect, useState } from "react";
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
  draft: "bg-neutral-100 text-neutral-700",
  approved: "bg-accent-50 text-accent-700",
  sent: "bg-warning-50 text-warning-700",
  paid: "bg-success-50 text-success-700",
  overdue: "bg-danger-50 text-danger-700",
  cancelled: "bg-danger-50 text-danger",
};

const PEPPOL_COLORS: Record<string, string> = {
  pending: "bg-warning-50 text-warning",
  sent: "bg-accent-50 text-accent",
  delivered: "bg-success-50 text-success",
  failed: "bg-danger-50 text-danger",
};

function formatCents(cents: number): string {
  return (cents / 100).toFixed(2) + " \u20ac";
}

export default function InvoiceList() {
  const { data: session } = useSession();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loadingLines, setLoadingLines] = useState<string | null>(null);

  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;

  useEffect(() => {
    if (!token) return;
    apiFetch<{ items: Invoice[] }>("/invoices", token, { tenantId })
      .then((data) => setInvoices(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token, tenantId]);

  const toggleExpand = async (invoice: Invoice) => {
    if (expandedId === invoice.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(invoice.id);
    if (!invoice.lines && token) {
      setLoadingLines(invoice.id);
      try {
        const detail = await apiFetch<Invoice>(`/invoices/${invoice.id}`, token, { tenantId });
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
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div />
        <button className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Cr&eacute;er facture
        </button>
      </div>

      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md mb-4 text-sm">{error}</div>
      )}

      <div className="bg-white rounded-lg shadow-subtle overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-neutral-200">
              <th className="w-8 px-3 py-3"></th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">Num&eacute;ro</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">HT</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">TVA</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">TTC</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">Statut</th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">Peppol</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {invoices.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-sm text-neutral-400">
                  Aucune facture trouv&eacute;e.
                </td>
              </tr>
            ) : (
              invoices.map((inv) => (
                <Fragment key={inv.id}>
                  <tr
                    onClick={() => toggleExpand(inv)}
                    className="hover:bg-neutral-50 transition-colors cursor-pointer"
                  >
                    <td className="px-3 py-4 text-neutral-400">
                      {expandedId === inv.id ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-accent">{inv.invoice_number}</td>
                    <td className="px-6 py-4 text-sm text-neutral-900">{formatCents(inv.subtotal_cents)}</td>
                    <td className="px-6 py-4 text-sm text-neutral-500">{formatCents(inv.vat_cents)}</td>
                    <td className="px-6 py-4 text-sm font-semibold text-neutral-900">{formatCents(inv.total_cents)}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[inv.status] || "bg-neutral-100 text-neutral-700"}`}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {inv.peppol_status && (
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${PEPPOL_COLORS[inv.peppol_status] || "bg-neutral-100 text-neutral-600"}`}>
                          {inv.peppol_status}
                        </span>
                      )}
                    </td>
                  </tr>
                  {expandedId === inv.id && (
                    <tr key={`${inv.id}-lines`}>
                      <td colSpan={7} className="px-10 py-4 bg-neutral-50">
                        {loadingLines === inv.id ? (
                          <Loader2 className="w-5 h-5 animate-spin text-neutral-400" />
                        ) : inv.lines && inv.lines.length > 0 ? (
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="text-xs text-neutral-500 uppercase">
                                <th className="text-left py-1">Description</th>
                                <th className="text-right py-1">Qt&eacute;</th>
                                <th className="text-right py-1">PU</th>
                                <th className="text-right py-1">Total</th>
                              </tr>
                            </thead>
                            <tbody>
                              {inv.lines.map((line) => (
                                <tr key={line.id} className="border-t border-neutral-200">
                                  <td className="py-2 text-neutral-700">{line.description}</td>
                                  <td className="py-2 text-right text-neutral-500">{line.quantity}</td>
                                  <td className="py-2 text-right text-neutral-500">{formatCents(line.unit_price_cents)}</td>
                                  <td className="py-2 text-right font-medium text-neutral-900">{formatCents(line.total_cents)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : (
                          <p className="text-neutral-400 text-sm">Aucune ligne.</p>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
