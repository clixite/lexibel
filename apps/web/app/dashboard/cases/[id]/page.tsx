"use client";

import { useSession } from "next-auth/react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Loader2, ArrowLeft, Edit, Plus, Clock, User, FileText, Calendar } from "lucide-react";

interface Case {
  id: string;
  reference: string;
  title: string;
  matter_type: string;
  status: "open" | "in_progress" | "pending" | "closed";
  jurisdiction: string;
  opened_at: string;
  closed_at: string | null;
  description: string | null;
  client_id: string | null;
  assigned_lawyer_id: string | null;
}

interface CaseContact {
  id: string;
  contact_id: string;
  role: string;
  contact: {
    id: string;
    name: string;
    email: string;
    phone: string | null;
    type: string;
  };
}

interface TimeEntry {
  id: string;
  date: string;
  duration_minutes: number;
  description: string;
  billable: boolean;
  billable_amount: number | null;
  user: {
    id: string;
    name: string;
  };
}

interface TimelineEvent {
  id: string;
  event_type: string;
  event_date: string;
  description: string;
  user: {
    id: string;
    name: string;
  } | null;
}

type TabType = "resume" | "contacts" | "documents" | "prestations" | "timeline";

export default function CaseDetailPage() {
  const { data: session } = useSession();
  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;

  const [activeTab, setActiveTab] = useState<TabType>("resume");
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [contacts, setContacts] = useState<CaseContact[]>([]);
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [tabLoading, setTabLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && tenantId) {
      fetchCase();
    }
  }, [token, tenantId, caseId]);

  useEffect(() => {
    if (token && tenantId && caseData) {
      loadTabData();
    }
  }, [activeTab, token, tenantId, caseData]);

  const fetchCase = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiFetch(`/cases/${caseId}`, token, { tenantId });
      setCaseData(data);
    } catch (err: any) {
      setError(err.message || "Erreur lors du chargement du dossier");
    } finally {
      setLoading(false);
    }
  };

  const loadTabData = async () => {
    try {
      setTabLoading(true);
      if (activeTab === "contacts") {
        const data = await apiFetch(`/cases/${caseId}/contacts`, token, { tenantId });
        setContacts(data);
      } else if (activeTab === "prestations") {
        const data = await apiFetch(`/time-entries?case_id=${caseId}`, token, { tenantId });
        setTimeEntries(data);
      } else if (activeTab === "timeline") {
        const data = await apiFetch(`/cases/${caseId}/timeline`, token, { tenantId });
        setTimeline(data);
      }
    } catch (err: any) {
      console.error("Error loading tab data:", err);
    } finally {
      setTabLoading(false);
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "open":
        return "bg-success-50 text-success-700";
      case "closed":
        return "bg-neutral-100 text-neutral-600";
      case "pending":
        return "bg-warning-50 text-warning-700";
      case "in_progress":
        return "bg-accent-50 text-accent-700";
      default:
        return "bg-neutral-100 text-neutral-600";
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "open":
        return "Ouvert";
      case "closed":
        return "Fermé";
      case "pending":
        return "En attente";
      case "in_progress":
        return "En cours";
      default:
        return status;
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "—";
    return new Date(dateString).toLocaleDateString("fr-BE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  };

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours === 0) return `${mins}m`;
    if (mins === 0) return `${hours}h`;
    return `${hours}h ${mins}m`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="p-6">
        <div className="card bg-danger-50 border-danger-200">
          <p className="text-danger-700">{error || "Dossier introuvable"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <button
            onClick={() => router.push("/dashboard/cases")}
            className="mt-1 text-neutral-500 hover:text-neutral-700"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-semibold text-neutral-900">
                {caseData.reference} - {caseData.title}
              </h1>
              <span className={`px-3 py-1 text-sm font-medium rounded-full ${getStatusBadgeClass(caseData.status)}`}>
                {getStatusLabel(caseData.status)}
              </span>
            </div>
            <p className="text-neutral-500">{caseData.matter_type}</p>
          </div>
        </div>
        <button
          onClick={() => router.push(`/dashboard/cases/${caseId}/edit`)}
          className="btn-primary flex items-center gap-2"
        >
          <Edit className="w-4 h-4" />
          Modifier
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-neutral-200">
        <div className="flex gap-6">
          {[
            { id: "resume", label: "Résumé", icon: FileText },
            { id: "contacts", label: "Contacts", icon: User },
            { id: "documents", label: "Documents", icon: FileText },
            { id: "prestations", label: "Prestations", icon: Clock },
            { id: "timeline", label: "Timeline", icon: Calendar },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`flex items-center gap-2 px-1 py-3 border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? "border-primary-600 text-primary-600"
                    : "border-transparent text-neutral-500 hover:text-neutral-700"
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {activeTab === "resume" && (
          <div className="card space-y-6">
            <h2 className="text-lg font-semibold text-neutral-900">Informations générales</h2>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-neutral-500 mb-1">
                  Référence
                </label>
                <p className="text-neutral-900">{caseData.reference}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-500 mb-1">
                  Titre
                </label>
                <p className="text-neutral-900">{caseData.title}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-500 mb-1">
                  Type d'affaire
                </label>
                <p className="text-neutral-900">{caseData.matter_type}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-500 mb-1">
                  Statut
                </label>
                <span className={`inline-block px-3 py-1 text-sm font-medium rounded-full ${getStatusBadgeClass(caseData.status)}`}>
                  {getStatusLabel(caseData.status)}
                </span>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-500 mb-1">
                  Juridiction
                </label>
                <p className="text-neutral-900">{caseData.jurisdiction}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-500 mb-1">
                  Date d'ouverture
                </label>
                <p className="text-neutral-900">{formatDate(caseData.opened_at)}</p>
              </div>
              {caseData.closed_at && (
                <div>
                  <label className="block text-sm font-medium text-neutral-500 mb-1">
                    Date de clôture
                  </label>
                  <p className="text-neutral-900">{formatDate(caseData.closed_at)}</p>
                </div>
              )}
            </div>
            {caseData.description && (
              <div>
                <label className="block text-sm font-medium text-neutral-500 mb-1">
                  Description
                </label>
                <p className="text-neutral-900 whitespace-pre-wrap">{caseData.description}</p>
              </div>
            )}
          </div>
        )}

        {activeTab === "contacts" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-neutral-900">Contacts liés</h2>
              <button
                onClick={() => router.push(`/dashboard/cases/${caseId}/contacts/link`)}
                className="btn-primary flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Lier un contact
              </button>
            </div>
            {tabLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
              </div>
            ) : contacts.length === 0 ? (
              <div className="card text-center py-12">
                <User className="w-12 h-12 mx-auto mb-4 text-neutral-400" />
                <p className="text-neutral-500">Aucun contact lié à ce dossier</p>
              </div>
            ) : (
              <div className="space-y-3">
                {contacts.map((caseContact) => (
                  <div key={caseContact.id} className="card hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4">
                        <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
                          <User className="w-5 h-5 text-primary-600" />
                        </div>
                        <div>
                          <h3 className="font-medium text-neutral-900">
                            {caseContact.contact.name}
                          </h3>
                          <p className="text-sm text-neutral-500">{caseContact.role}</p>
                          <div className="mt-2 space-y-1">
                            {caseContact.contact.email && (
                              <p className="text-sm text-neutral-600">
                                {caseContact.contact.email}
                              </p>
                            )}
                            {caseContact.contact.phone && (
                              <p className="text-sm text-neutral-600">
                                {caseContact.contact.phone}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                      <span className="px-2 py-1 text-xs font-medium bg-neutral-100 text-neutral-600 rounded">
                        {caseContact.contact.type}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "documents" && (
          <div className="card text-center py-12">
            <FileText className="w-12 h-12 mx-auto mb-4 text-neutral-400" />
            <p className="text-neutral-500">Bientôt disponible</p>
          </div>
        )}

        {activeTab === "prestations" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-neutral-900">Prestations</h2>
              <button
                onClick={() => router.push(`/dashboard/time-entries/new?case_id=${caseId}`)}
                className="btn-primary flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Nouvelle prestation
              </button>
            </div>
            {tabLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
              </div>
            ) : timeEntries.length === 0 ? (
              <div className="card text-center py-12">
                <Clock className="w-12 h-12 mx-auto mb-4 text-neutral-400" />
                <p className="text-neutral-500">Aucune prestation enregistrée</p>
              </div>
            ) : (
              <div className="space-y-3">
                {timeEntries.map((entry) => (
                  <div key={entry.id} className="card hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-sm font-medium text-neutral-900">
                            {formatDate(entry.date)}
                          </span>
                          <span className="text-sm text-neutral-500">
                            {entry.user.name}
                          </span>
                          <span className="flex items-center gap-1 text-sm text-neutral-600">
                            <Clock className="w-3 h-3" />
                            {formatDuration(entry.duration_minutes)}
                          </span>
                        </div>
                        <p className="text-neutral-700">{entry.description}</p>
                      </div>
                      <div className="text-right">
                        {entry.billable ? (
                          <div>
                            <span className="text-xs font-medium text-success-600 bg-success-50 px-2 py-1 rounded">
                              Facturable
                            </span>
                            {entry.billable_amount && (
                              <p className="mt-1 text-sm font-medium text-neutral-900">
                                {entry.billable_amount.toFixed(2)} €
                              </p>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs font-medium text-neutral-500 bg-neutral-100 px-2 py-1 rounded">
                            Non facturable
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "timeline" && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-neutral-900">Chronologie</h2>
            {tabLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
              </div>
            ) : timeline.length === 0 ? (
              <div className="card text-center py-12">
                <Calendar className="w-12 h-12 mx-auto mb-4 text-neutral-400" />
                <p className="text-neutral-500">Aucun événement dans la chronologie</p>
              </div>
            ) : (
              <div className="relative">
                <div className="absolute left-4 top-0 bottom-0 w-px bg-neutral-200"></div>
                <div className="space-y-6">
                  {timeline.map((event, index) => (
                    <div key={event.id} className="relative flex gap-4">
                      <div className="relative z-10 w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
                        <div className="w-3 h-3 rounded-full bg-primary-600"></div>
                      </div>
                      <div className="card flex-1 mt-0.5">
                        <div className="flex items-start justify-between mb-2">
                          <h3 className="font-medium text-neutral-900">{event.event_type}</h3>
                          <span className="text-sm text-neutral-500">
                            {formatDate(event.event_date)}
                          </span>
                        </div>
                        <p className="text-neutral-700 mb-2">{event.description}</p>
                        {event.user && (
                          <p className="text-sm text-neutral-500">Par {event.user.name}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
