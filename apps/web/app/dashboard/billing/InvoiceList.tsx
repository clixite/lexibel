"use client";

import { useSession } from "next-auth/react";
import { Fragment, useEffect, useState } from "react";
import { Plus, ChevronDown, ChevronRight, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";
import SkeletonList from "@/components/skeletons/SkeletonList";
import Badge from "@/components/ui/Badge";

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
    return <SkeletonList />;
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

      <div className="bg-white rounded-xl shadow-md border border-neutral-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gradient-to-r from-neutral-50 to-neutral-100 border-b border-neutral-200">
                <th className="w-8 px-3 py-4"></th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-700 uppercase tracking-wider">Numéro</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-700 uppercase tracking-wider">HT</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-700 uppercase tracking-wider">TVA</th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-700 uppercase tracking-wider">TTC</th>
                <th className="text-center px-6 py-4 text-xs font-semibold text-neutral-700 uppercase tracking-wider">Statut</th>
                <th className="text-center px-6 py-4 text-xs font-semibold text-neutral-700 uppercase tracking-wider">Peppol</th>
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
              invoices.map((inv) => {
                const getStatusBadgeVariant = (status: string): "default" | "success" | "warning" | "danger" | "accent" | "neutral" => {
                  const variantMap: Record<string, "default" | "success" | "warning" | "danger" | "accent" | "neutral"> = {
                    draft: "neutral",
                    approved: "accent",
                    sent: "warning",
                    paid: "success",
                    overdue: "danger",
                    cancelled: "danger",
                  };
                  return variantMap[status] || "default";
                };

                const getPeppolBadgeVariant = (status: string): "default" | "success" | "warning" | "danger" | "accent" | "neutral" => {
                  const variantMap: Record<string, "default" | "success" | "warning" | "danger" | "accent" | "neutral"> = {
                    pending: "warning",
                    sent: "accent",
                    delivered: "success",
                    failed: "danger",
                  };
                  return variantMap[status] || "default";
                };

                return (
                  <Fragment key={inv.id}>
                    <tr
                      onClick={() => toggleExpand(inv)}
                      className="hover:bg-neutral-50/50 transition-all duration-200 cursor-pointer group"
                    >
                      <td className="px-3 py-4 text-neutral-400 group-hover:text-accent transition-colors">
                        {expandedId === inv.id ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm font-semibold text-accent group-hover:text-accent-700 transition-colors">{inv.invoice_number}</td>
                      <td className="px-6 py-4 text-sm text-neutral-900">{formatCents(inv.subtotal_cents)}</td>
                      <td className="px-6 py-4 text-sm text-neutral-600">{formatCents(inv.vat_cents)}</td>
                      <td className="px-6 py-4 text-sm font-semibold text-neutral-900">{formatCents(inv.total_cents)}</td>
                      <td className="px-6 py-4 text-center">
                        <Badge variant={getStatusBadgeVariant(inv.status)} size="sm" dot>
                          {inv.status}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-center">
                        {inv.peppol_status && (
                          <Badge variant={getPeppolBadgeVariant(inv.peppol_status)} size="sm" dot>
                            {inv.peppol_status}
                          </Badge>
                        )}
                      </td>
                    </tr>
                    {expandedId === inv.id && (
                      <tr key={`${inv.id}-lines`}>
                        <td colSpan={7} className="px-10 py-6 bg-gradient-to-r from-neutral-50/50 to-white border-t border-neutral-100">
                          {loadingLines === inv.id ? (
                            <div className="flex items-center justify-center py-4">
                              <Loader2 className="w-5 h-5 animate-spin text-accent" />
                            </div>
                          ) : inv.lines && inv.lines.length > 0 ? (
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="text-xs text-neutral-600 uppercase font-semibold">
                                  <th className="text-left py-2 px-3">Description</th>
                                  <th className="text-right py-2 px-3">Qté</th>
                                  <th className="text-right py-2 px-3">PU</th>
                                  <th className="text-right py-2 px-3">Total</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-neutral-100">
                                {inv.lines.map((line) => (
                                  <tr key={line.id} className="hover:bg-neutral-50/50 transition-colors">
                                    <td className="py-2 px-3 text-neutral-700">{line.description}</td>
                                    <td className="py-2 px-3 text-right text-neutral-600">{line.quantity}</td>
                                    <td className="py-2 px-3 text-right text-neutral-600">{formatCents(line.unit_price_cents)}</td>
                                    <td className="py-2 px-3 text-right font-semibold text-neutral-900">{formatCents(line.total_cents)}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          ) : (
                            <p className="text-neutral-400 text-sm py-2">Aucune ligne.</p>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })
            )}
            </tbody>
            </table>
        </div>
      </div>
    </div>
  );
}
