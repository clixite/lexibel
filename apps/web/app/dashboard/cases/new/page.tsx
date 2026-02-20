"use client";

import { useAuth } from "@/lib/useAuth";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { Button, Badge } from "@/components/ui";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Loader2,
  Scale,
  Shield,
  Building2,
  Users,
  Calculator,
  Heart,
  Landmark,
  Home,
  HardHat,
  Briefcase,
  Leaf,
  Lightbulb,
  Plus,
  X,
  Search,
  Brain,
  AlertTriangle,
  Clock,
  FileText,
  ChevronDown,
  Banknote,
  Calendar,
  Tag,
} from "lucide-react";

/* ──────────────────── CONSTANTS ──────────────────── */

const MATTER_TYPES = [
  { value: "civil", label: "Droit civil", icon: Scale, desc: "Responsabilite, baux, successions" },
  { value: "penal", label: "Droit penal", icon: Shield, desc: "Infractions, defence penale" },
  { value: "commercial", label: "Droit commercial", icon: Building2, desc: "Faillites, litiges commerciaux" },
  { value: "social", label: "Droit social", icon: Users, desc: "Travail, licenciements, ONSS" },
  { value: "fiscal", label: "Droit fiscal", icon: Calculator, desc: "IPP, ISOC, TVA, droits" },
  { value: "family", label: "Droit familial", icon: Heart, desc: "Divorce, garde, pensions" },
  { value: "administrative", label: "Droit administratif", icon: Landmark, desc: "Urbanisme, marches publics" },
  { value: "immobilier", label: "Droit immobilier", icon: Home, desc: "Ventes, baux, copropriete" },
  { value: "construction", label: "Droit de la construction", icon: HardHat, desc: "Vices, responsabilite decennale" },
  { value: "societes", label: "Droit des societes", icon: Briefcase, desc: "Constitution, AG, cessions" },
  { value: "environnement", label: "Droit de l'environnement", icon: Leaf, desc: "Permis, pollution, sols" },
  { value: "ip", label: "Propriete intellectuelle", icon: Lightbulb, desc: "Marques, brevets, droits d'auteur" },
];

const SUB_TYPES: Record<string, { value: string; label: string }[]> = {
  civil: [
    { value: "responsabilite_contractuelle", label: "Responsabilite contractuelle" },
    { value: "responsabilite_extracontractuelle", label: "Responsabilite extracontractuelle" },
    { value: "recouvrement", label: "Recouvrement de creances" },
    { value: "bail_habitation", label: "Bail d'habitation" },
    { value: "bail_commercial", label: "Bail commercial" },
    { value: "voisinage", label: "Troubles de voisinage" },
    { value: "servitudes", label: "Servitudes" },
    { value: "succession", label: "Succession" },
    { value: "donation", label: "Donation" },
    { value: "autre", label: "Autre" },
  ],
  penal: [
    { value: "vol", label: "Vol" },
    { value: "escroquerie", label: "Escroquerie" },
    { value: "abus_de_confiance", label: "Abus de confiance" },
    { value: "violence", label: "Coups et blessures" },
    { value: "roulage", label: "Roulage" },
    { value: "stupefiants", label: "Stupefiants" },
    { value: "droit_penal_social", label: "Droit penal social" },
    { value: "autre", label: "Autre" },
  ],
  commercial: [
    { value: "faillite", label: "Faillite" },
    { value: "prr", label: "PRJ (reorganisation judiciaire)" },
    { value: "contentieux_commercial", label: "Contentieux commercial" },
    { value: "concurrence", label: "Concurrence deloyale" },
    { value: "distribution", label: "Contrats de distribution" },
    { value: "autre", label: "Autre" },
  ],
  family: [
    { value: "divorce_consent", label: "Divorce par consentement mutuel" },
    { value: "divorce_cause", label: "Divorce pour desunion irremed." },
    { value: "pension_alimentaire", label: "Pension alimentaire" },
    { value: "garde_enfant", label: "Hebergement / Autorite parentale" },
    { value: "filiation", label: "Filiation" },
    { value: "adoption", label: "Adoption" },
    { value: "regime_matrimonial", label: "Regime matrimonial" },
    { value: "autre", label: "Autre" },
  ],
  social: [
    { value: "licenciement", label: "Licenciement" },
    { value: "accident_travail", label: "Accident du travail" },
    { value: "maladie_pro", label: "Maladie professionnelle" },
    { value: "harcelement", label: "Harcelement" },
    { value: "discrimination", label: "Discrimination" },
    { value: "securite_sociale", label: "Securite sociale" },
    { value: "autre", label: "Autre" },
  ],
  fiscal: [
    { value: "ipp", label: "Impot des personnes physiques" },
    { value: "isoc", label: "Impot des societes" },
    { value: "tva", label: "TVA" },
    { value: "droits_succession", label: "Droits de succession" },
    { value: "droits_enregistrement", label: "Droits d'enregistrement" },
    { value: "taxe_communale", label: "Taxes communales" },
    { value: "autre", label: "Autre" },
  ],
};

const BELGIAN_COURTS = [
  { value: "justice_paix", label: "Justice de paix" },
  { value: "tribunal_police", label: "Tribunal de police" },
  { value: "tribunal_premiere_instance", label: "Tribunal de premiere instance" },
  { value: "tribunal_entreprise", label: "Tribunal de l'entreprise" },
  { value: "tribunal_travail", label: "Tribunal du travail" },
  { value: "cour_appel", label: "Cour d'appel" },
  { value: "cour_travail", label: "Cour du travail" },
  { value: "cour_cassation", label: "Cour de cassation" },
  { value: "conseil_etat", label: "Conseil d'Etat" },
  { value: "cour_constitutionnelle", label: "Cour constitutionnelle" },
];

const ARRONDISSEMENTS = [
  "Bruxelles",
  "Nivelles",
  "Louvain (Leuven)",
  "Liege",
  "Namur",
  "Luxembourg",
  "Mons",
  "Charleroi",
  "Tournai",
  "Eupen",
  "Anvers (Antwerpen)",
  "Gand (Gent)",
  "Bruges (Brugge)",
  "Courtrai (Kortrijk)",
  "Termonde (Dendermonde)",
  "Hasselt",
  "Tongres (Tongeren)",
  "Turnhout",
  "Malines (Mechelen)",
];

const BILLING_TYPES = [
  { value: "hourly", label: "Taux horaire", desc: "Facturation a l'heure prestee" },
  { value: "forfait", label: "Forfait", desc: "Montant fixe pour l'ensemble du dossier" },
  { value: "pro_deo", label: "Pro Deo / Aide juridique", desc: "Intervention du BAJ" },
  { value: "mixed", label: "Mixte", desc: "Combinaison horaire + forfait" },
  { value: "success_fee", label: "Honoraire de resultat", desc: "Base + pourcentage du resultat" },
];

const STEPS = [
  { num: 1, label: "Type" },
  { num: 2, label: "Identification" },
  { num: 3, label: "Parties" },
  { num: 4, label: "Juridiction" },
  { num: 5, label: "Dates" },
  { num: 6, label: "Finances" },
  { num: 7, label: "Validation" },
];

/* ──────────────────── AI MOCK ──────────────────── */

interface AiAssist {
  suggested_jurisdiction: string | null;
  suggested_sub_type: string | null;
  applicable_deadlines: { name: string; duration: string; description: string }[];
  required_documents: string[];
  risk_points: string[];
  strategy_notes: string;
  estimated_complexity: string;
  belgian_legal_references: string[];
}

function generateMockAiAssist(matterType: string): AiAssist {
  const base: Record<string, Partial<AiAssist>> = {
    civil: {
      suggested_jurisdiction: "Tribunal de premiere instance",
      applicable_deadlines: [
        { name: "Prescription", duration: "10 ans", description: "Art. 2262bis C. civ. - actions personnelles" },
        { name: "Appel", duration: "1 mois", description: "Art. 1051 C. jud. - delai d'appel" },
      ],
      required_documents: ["Citation ou requete introductive", "Pieces justificatives", "Conclusions", "Bordereau de pieces", "Decompte detaille"],
      risk_points: ["Verifier la prescription", "Evaluer les chances de recouvrement", "Identifier les moyens de preuve disponibles"],
      strategy_notes: "Evaluer l'opportunite d'une mise en demeure prealable. Verifier si une mediation est envisageable avant d'introduire l'action. Preparer un dossier de pieces complet.",
      belgian_legal_references: ["Art. 1382-1386 C. civil", "Art. 700-1042 C. judiciaire", "Art. 2262bis C. civil"],
      estimated_complexity: "moderate",
    },
    penal: {
      suggested_jurisdiction: "Tribunal correctionnel",
      applicable_deadlines: [
        { name: "Prescription action publique", duration: "5 ans (delit)", description: "Art. 21 Titre prel. C.I.Cr." },
        { name: "Appel", duration: "30 jours", description: "Art. 203 C.I.Cr." },
      ],
      required_documents: ["PV de police", "Constitution de partie civile", "Pieces attestant le dommage", "Attestations medicales"],
      risk_points: ["Verifier la qualification penale", "Evaluer les preuves a charge", "Anticiper la constitution de partie civile"],
      strategy_notes: "Analyser les elements constitutifs de l'infraction. Verifier les vices de procedure eventuels. Preparer la strategie de defence.",
      belgian_legal_references: ["Code penal - Livre II", "Code d'instruction criminelle", "Loi du 17 avril 1878 (Titre prel.)"],
      estimated_complexity: "complex",
    },
    family: {
      suggested_jurisdiction: "Tribunal de la famille",
      applicable_deadlines: [
        { name: "Delai reflexion (DCM)", duration: "6 mois", description: "Art. 1289 C. jud." },
        { name: "Appel", duration: "1 mois", description: "Art. 1051 C. jud." },
      ],
      required_documents: ["Acte de mariage", "Actes de naissance enfants", "Attestations de revenus", "Inventaire du patrimoine", "Convention prealable (DCM)"],
      risk_points: ["Evaluer l'hebergement des enfants", "Calculer les pensions alimentaires", "Identifier le regime matrimonial"],
      strategy_notes: "Privilegier une approche collaborative si possible. Preparer le dossier financier complet. Evaluer les mesures urgentes et provisoires.",
      belgian_legal_references: ["Art. 229-231 C. civil", "Art. 1253ter-1253octies C. jud.", "Art. 203-203bis C. civil"],
      estimated_complexity: "moderate",
    },
    commercial: {
      suggested_jurisdiction: "Tribunal de l'entreprise",
      applicable_deadlines: [
        { name: "Prescription commerciale", duration: "10 ans", description: "Art. 2262bis C. civ." },
        { name: "Opposition faillite", duration: "15 jours", description: "Art. XX.108 CDE" },
      ],
      required_documents: ["Contrats commerciaux", "Factures et bons de commande", "Correspondances", "Extraits BCE", "Comptes annuels"],
      risk_points: ["Verifier la competence du tribunal de l'entreprise", "Evaluer la solvabilite du debiteur", "Envisager les mesures conservatoires"],
      strategy_notes: "Analyser la solidite des preuves contractuelles. Verifier les clauses d'arbitrage. Evaluer l'opportunite de mesures conservatoires.",
      belgian_legal_references: ["Code de droit economique (CDE)", "Art. 1382 C. civil", "Loi sur les faillites"],
      estimated_complexity: "moderate",
    },
    social: {
      suggested_jurisdiction: "Tribunal du travail",
      applicable_deadlines: [
        { name: "Contestation licenciement", duration: "1 an", description: "Art. 15 Loi du 3/7/1978" },
        { name: "Appel", duration: "1 mois", description: "Art. 1051 C. jud." },
      ],
      required_documents: ["Contrat de travail", "Lettre de licenciement", "Fiches de paie", "C4", "Reglement de travail"],
      risk_points: ["Verifier le motif du licenciement (CCT 109)", "Calculer l'indemnite compensatoire", "Identifier les protections speciales"],
      strategy_notes: "Analyser le motif de licenciement au regard de la CCT 109. Verifier le respect de la procedure Renault si applicable. Calculer toutes les indemnites.",
      belgian_legal_references: ["Loi du 3 juillet 1978", "CCT n.109", "Loi du 26 decembre 2013 (statut unique)"],
      estimated_complexity: "moderate",
    },
    fiscal: {
      suggested_jurisdiction: "Tribunal de premiere instance (chambre fiscale)",
      applicable_deadlines: [
        { name: "Reclamation", duration: "6 mois", description: "Art. 371 CIR 1992" },
        { name: "Action en justice", duration: "3 mois apres decision", description: "Art. 1385undecies C. jud." },
      ],
      required_documents: ["Avertissement-extrait de role", "Declaration fiscale", "Reclamation administrative", "Decision directoriale"],
      risk_points: ["Respecter strictement les delais de reclamation", "Verifier la motivation de l'imposition", "Identifier les vices de procedure"],
      strategy_notes: "Toujours commencer par la reclamation administrative. Verifier les delais d'imposition. Analyser la charge de la preuve.",
      belgian_legal_references: ["CIR 1992 - Art. 371 et suivants", "Code TVA - Art. 84-91", "Art. 1385undecies C. judiciaire"],
      estimated_complexity: "complex",
    },
  };

  const data = base[matterType] || base.civil;
  return {
    suggested_jurisdiction: data.suggested_jurisdiction || "Tribunal de premiere instance",
    suggested_sub_type: null,
    applicable_deadlines: data.applicable_deadlines || [],
    required_documents: data.required_documents || [],
    risk_points: data.risk_points || [],
    strategy_notes: data.strategy_notes || "",
    estimated_complexity: data.estimated_complexity || "moderate",
    belgian_legal_references: data.belgian_legal_references || [],
  };
}

/* ──────────────────── INTERFACES ──────────────────── */

interface Party {
  id: string;
  name: string;
  type: "natural" | "legal";
  email: string;
  phone: string;
  contact_id: string | null;
  counsel_name: string;
  counsel_bar: string;
}

interface Deadline {
  id: string;
  date: string;
  description: string;
  type: string;
}

interface FormState {
  // Step 1
  matter_type: string;
  sub_type: string;
  priority: string;
  // Step 2
  reference: string;
  title: string;
  description: string;
  tags: string[];
  // Step 3
  clients: Party[];
  adverse: Party[];
  others: Party[];
  // Step 4
  tribunal: string;
  arrondissement: string;
  chambre: string;
  court_reference: string;
  proc_language: string;
  // Step 5
  opened_at: string;
  prescription_date: string;
  next_hearing_date: string;
  next_hearing_time: string;
  deadlines: Deadline[];
  // Step 6
  billing_type: string;
  hourly_rate: string;
  fixed_amount: string;
  provision: string;
  budget_estimate: string;
  success_fee_pct: string;
  legal_aid: boolean;
  baj_reference: string;
  baj_type: string;
}

interface SearchResult {
  id: string;
  full_name: string;
  type: string;
  email: string | null;
  phone_e164: string | null;
}

/* ──────────────────── COMPONENT ──────────────────── */

function generateReference(): string {
  const year = new Date().getFullYear();
  const num = String(Math.floor(Math.random() * 9999) + 1).padStart(4, "0");
  return `DOS-${year}-${num}`;
}

function emptyParty(): Party {
  return { id: crypto.randomUUID(), name: "", type: "natural", email: "", phone: "", contact_id: null, counsel_name: "", counsel_bar: "" };
}

export default function NewCasePage() {
  const { accessToken, tenantId, userId } = useAuth();
  const router = useRouter();

  const [step, setStep] = useState(1);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState<FormState>({
    matter_type: "",
    sub_type: "",
    priority: "normal",
    reference: generateReference(),
    title: "",
    description: "",
    tags: [],
    clients: [],
    adverse: [],
    others: [],
    tribunal: "",
    arrondissement: "",
    chambre: "",
    court_reference: "",
    proc_language: "fr",
    opened_at: new Date().toISOString().slice(0, 10),
    prescription_date: "",
    next_hearing_date: "",
    next_hearing_time: "",
    deadlines: [],
    billing_type: "hourly",
    hourly_rate: "150",
    fixed_amount: "",
    provision: "",
    budget_estimate: "",
    success_fee_pct: "",
    legal_aid: false,
    baj_reference: "",
    baj_type: "deuxieme_ligne",
  });

  // Tag input
  const [tagInput, setTagInput] = useState("");

  // Party search
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchingContacts, setSearchingContacts] = useState(false);
  const [addingTo, setAddingTo] = useState<"clients" | "adverse" | "others" | null>(null);
  const [showNewParty, setShowNewParty] = useState(false);

  // AI assist
  const [aiData, setAiData] = useState<AiAssist | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  const updateForm = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((f) => ({ ...f, [key]: value }));
  };

  /* ── Contact Search ── */
  const searchContacts = async (q: string) => {
    if (!q || q.length < 2 || !accessToken) return;
    setSearchingContacts(true);
    try {
      const data = await apiFetch<{ items: SearchResult[] }>(`/contacts/search?q=${encodeURIComponent(q)}`, accessToken, { tenantId });
      setSearchResults(data.items || []);
    } catch {
      setSearchResults([]);
    } finally {
      setSearchingContacts(false);
    }
  };

  useEffect(() => {
    const t = setTimeout(() => searchContacts(searchQuery), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery]);

  const addPartyFromSearch = (contact: SearchResult, target: "clients" | "adverse" | "others") => {
    const party: Party = {
      id: crypto.randomUUID(),
      name: contact.full_name,
      type: contact.type as "natural" | "legal",
      email: contact.email || "",
      phone: contact.phone_e164 || "",
      contact_id: contact.id,
      counsel_name: "",
      counsel_bar: "",
    };
    updateForm(target, [...form[target], party]);
    setAddingTo(null);
    setSearchQuery("");
    setSearchResults([]);
  };

  const addNewParty = (target: "clients" | "adverse" | "others") => {
    updateForm(target, [...form[target], emptyParty()]);
    setShowNewParty(false);
    setAddingTo(null);
  };

  const removeParty = (target: "clients" | "adverse" | "others", id: string) => {
    updateForm(target, form[target].filter((p) => p.id !== id));
  };

  const updateParty = (target: "clients" | "adverse" | "others", id: string, field: keyof Party, value: string) => {
    updateForm(target, form[target].map((p) => (p.id === id ? { ...p, [field]: value } : p)));
  };

  /* ── Tags ── */
  const addTag = () => {
    const tag = tagInput.trim().toLowerCase();
    if (tag && !form.tags.includes(tag)) {
      updateForm("tags", [...form.tags, tag]);
    }
    setTagInput("");
  };

  /* ── Deadlines ── */
  const addDeadline = () => {
    updateForm("deadlines", [...form.deadlines, { id: crypto.randomUUID(), date: "", description: "", type: "legal" }]);
  };

  const removeDeadline = (id: string) => {
    updateForm("deadlines", form.deadlines.filter((d) => d.id !== id));
  };

  /* ── AI ── */
  const fetchAiAssist = async () => {
    if (!accessToken || !form.matter_type) return;
    setAiLoading(true);
    try {
      const data = await apiFetch<AiAssist>("/brain/dossier/assist-creation", accessToken, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          matter_type: form.matter_type,
          description: form.description,
          client_name: form.clients[0]?.name || null,
        }),
      });
      setAiData(data);
    } catch {
      setAiData(generateMockAiAssist(form.matter_type));
    } finally {
      setAiLoading(false);
    }
  };

  /* ── Validation ── */
  const canNext = (): boolean => {
    if (step === 1) return !!form.matter_type;
    if (step === 2) return !!form.title.trim();
    return true;
  };

  /* ── Submit ── */
  const handleSubmit = async () => {
    if (!accessToken) return;
    setCreating(true);
    setError(null);

    const courtLabel = BELGIAN_COURTS.find((c) => c.value === form.tribunal)?.label || form.tribunal;
    const jurisdiction = courtLabel + (form.arrondissement ? ` de ${form.arrondissement}` : "");

    try {
      const res = await apiFetch<{ id: string }>("/cases", accessToken, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          reference: form.reference,
          title: form.title,
          matter_type: form.matter_type,
          status: "open",
          jurisdiction: jurisdiction || null,
          court_reference: form.court_reference || null,
          responsible_user_id: userId,
          opened_at: form.opened_at || null,
          metadata: {
            description: form.description,
            sub_type: form.sub_type || null,
            priority: form.priority,
            tags: form.tags,
            legal_aid: { enabled: form.legal_aid, baj_reference: form.baj_reference, type: form.baj_type },
            court: { name: courtLabel, chamber: form.chambre, location: form.arrondissement, language: form.proc_language },
            billing: {
              type: form.billing_type,
              hourly_rate: form.hourly_rate ? Number(form.hourly_rate) : null,
              fixed_amount: form.fixed_amount ? Number(form.fixed_amount) : null,
              provision: form.provision ? Number(form.provision) : null,
              budget_estimate: form.budget_estimate ? Number(form.budget_estimate) : null,
              success_fee_pct: form.success_fee_pct ? Number(form.success_fee_pct) : null,
            },
            key_dates: {
              prescription: form.prescription_date || null,
              next_hearing: form.next_hearing_date || null,
              next_hearing_time: form.next_hearing_time || null,
              deadlines: form.deadlines,
            },
            parties: {
              clients: form.clients.map((p) => ({ name: p.name, contact_id: p.contact_id, email: p.email, phone: p.phone })),
              adverse: form.adverse.map((p) => ({ name: p.name, contact_id: p.contact_id, email: p.email, phone: p.phone, counsel_name: p.counsel_name, counsel_bar: p.counsel_bar })),
              others: form.others.map((p) => ({ name: p.name, contact_id: p.contact_id, role: "other" })),
            },
          },
        }),
      });
      router.push(`/dashboard/cases/${res.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur lors de la creation");
    } finally {
      setCreating(false);
    }
  };

  /* ──────────────────── RENDER HELPERS ──────────────────── */

  const renderPartyList = (target: "clients" | "adverse" | "others", label: string) => (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-neutral-800">{label}</h4>
        <button
          type="button"
          onClick={() => { setAddingTo(target); setShowNewParty(false); setSearchQuery(""); }}
          className="flex items-center gap-1 text-xs text-accent-600 hover:text-accent-700 font-medium"
        >
          <Plus className="w-3.5 h-3.5" /> Ajouter
        </button>
      </div>

      {form[target].map((p) => (
        <div key={p.id} className="bg-neutral-50 rounded border border-neutral-200 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-neutral-900">{p.name || "Nouveau"}</span>
            <button type="button" onClick={() => removeParty(target, p.id)} className="text-neutral-400 hover:text-red-500">
              <X className="w-4 h-4" />
            </button>
          </div>
          {!p.contact_id && (
            <div className="grid grid-cols-2 gap-2">
              <input type="text" placeholder="Nom complet" value={p.name} onChange={(e) => updateParty(target, p.id, "name", e.target.value)} className="input text-sm py-1.5" />
              <input type="email" placeholder="Email" value={p.email} onChange={(e) => updateParty(target, p.id, "email", e.target.value)} className="input text-sm py-1.5" />
            </div>
          )}
          {target === "adverse" && (
            <div className="grid grid-cols-2 gap-2">
              <input type="text" placeholder="Avocat adverse" value={p.counsel_name} onChange={(e) => updateParty(target, p.id, "counsel_name", e.target.value)} className="input text-sm py-1.5" />
              <input type="text" placeholder="Barreau" value={p.counsel_bar} onChange={(e) => updateParty(target, p.id, "counsel_bar", e.target.value)} className="input text-sm py-1.5" />
            </div>
          )}
        </div>
      ))}

      {/* Add party panel */}
      {addingTo === target && (
        <div className="bg-white rounded border border-accent-200 p-3 space-y-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
            <input
              type="text"
              placeholder="Rechercher un contact existant..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-9 text-sm py-1.5 w-full"
              autoFocus
            />
          </div>
          {searchingContacts && <div className="text-xs text-neutral-500 flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Recherche...</div>}
          {searchResults.length > 0 && (
            <div className="max-h-32 overflow-y-auto space-y-1">
              {searchResults.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => addPartyFromSearch(c, target)}
                  className="w-full text-left px-3 py-2 text-sm rounded hover:bg-accent-50 flex items-center justify-between"
                >
                  <span className="font-medium">{c.full_name}</span>
                  <span className="text-xs text-neutral-400">{c.type === "legal" ? "Personne morale" : "Personne physique"}</span>
                </button>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <button type="button" onClick={() => addNewParty(target)} className="text-xs text-accent-600 hover:underline font-medium">Creer manuellement</button>
            <button type="button" onClick={() => setAddingTo(null)} className="text-xs text-neutral-500 hover:underline">Annuler</button>
          </div>
        </div>
      )}

      {form[target].length === 0 && addingTo !== target && (
        <p className="text-xs text-neutral-400 italic">Aucune partie ajoutee</p>
      )}
    </div>
  );

  /* ──────────────────── STEPS ──────────────────── */

  const renderStep1 = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-semibold text-neutral-900 mb-3">Matiere principale</label>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {MATTER_TYPES.map((mt) => {
            const Icon = mt.icon;
            const selected = form.matter_type === mt.value;
            return (
              <button
                key={mt.value}
                type="button"
                onClick={() => { updateForm("matter_type", mt.value); updateForm("sub_type", ""); }}
                className={`p-4 rounded-lg border-2 text-left transition-all ${
                  selected ? "border-accent bg-accent-50 shadow-sm" : "border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50"
                }`}
              >
                <Icon className={`w-5 h-5 mb-2 ${selected ? "text-accent-600" : "text-neutral-400"}`} />
                <div className={`text-sm font-semibold ${selected ? "text-accent-700" : "text-neutral-700"}`}>{mt.label}</div>
                <div className="text-xs text-neutral-500 mt-0.5">{mt.desc}</div>
              </button>
            );
          })}
        </div>
      </div>

      {form.matter_type && SUB_TYPES[form.matter_type] && (
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-2">Sous-type</label>
          <select value={form.sub_type} onChange={(e) => updateForm("sub_type", e.target.value)} className="input max-w-md">
            <option value="">-- Selectionnez --</option>
            {SUB_TYPES[form.matter_type].map((st) => (
              <option key={st.value} value={st.value}>{st.label}</option>
            ))}
          </select>
        </div>
      )}

      <div>
        <label className="block text-sm font-semibold text-neutral-900 mb-2">Priorite</label>
        <div className="flex gap-3">
          {[
            { value: "normal", label: "Normal", color: "bg-neutral-100 border-neutral-300 text-neutral-700" },
            { value: "urgent", label: "Urgent", color: "bg-warning-50 border-warning-300 text-warning-700" },
            { value: "tres_urgent", label: "Tres urgent", color: "bg-red-50 border-red-300 text-red-700" },
          ].map((p) => (
            <button
              key={p.value}
              type="button"
              onClick={() => updateForm("priority", p.value)}
              className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-all ${
                form.priority === p.value ? p.color + " shadow-sm" : "border-neutral-200 text-neutral-500 hover:border-neutral-300"
              }`}
            >
              {p.value === "tres_urgent" && <AlertTriangle className="w-3.5 h-3.5 inline mr-1" />}
              {p.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Reference interne</label>
          <input type="text" value={form.reference} onChange={(e) => updateForm("reference", e.target.value)} className="input" placeholder="DOS-2026-0001" />
          <p className="text-xs text-neutral-400 mt-1">Generee automatiquement, modifiable</p>
        </div>
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Matiere</label>
          <div className="input bg-neutral-50 text-neutral-600 cursor-not-allowed">
            {MATTER_TYPES.find((m) => m.value === form.matter_type)?.label || form.matter_type}
          </div>
        </div>
      </div>

      <div>
        <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Intitule du dossier <span className="text-red-500">*</span></label>
        <input type="text" value={form.title} onChange={(e) => updateForm("title", e.target.value)} className="input text-lg" placeholder="Ex: Dupont c/ SA Immobel - Bail commercial" />
      </div>

      <div>
        <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Resume des faits</label>
        <textarea value={form.description} onChange={(e) => updateForm("description", e.target.value)} rows={5} className="input" placeholder="Decrivez brievement les faits, le contexte et l'objet du litige..." />
      </div>

      <div>
        <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Mots-cles</label>
        <div className="flex gap-2 items-center flex-wrap mb-2">
          {form.tags.map((t) => (
            <span key={t} className="inline-flex items-center gap-1 bg-accent-50 text-accent-700 text-xs font-medium px-2.5 py-1 rounded">
              {t}
              <button type="button" onClick={() => updateForm("tags", form.tags.filter((x) => x !== t))}><X className="w-3 h-3" /></button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }}
            className="input flex-1"
            placeholder="Ajouter un mot-cle..."
          />
          <Button variant="secondary" size="sm" onClick={addTag} disabled={!tagInput.trim()}>
            <Tag className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {renderPartyList("clients", "Partie(s) requerante(s) / Client(s)")}
      {renderPartyList("adverse", "Partie(s) adverse(s)")}
      <div className="md:col-span-2">
        {renderPartyList("others", "Autres intervenants (experts, temoins, tiers)")}
      </div>
    </div>
  );

  const renderStep4 = () => (
    <div className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Tribunal</label>
          <select value={form.tribunal} onChange={(e) => updateForm("tribunal", e.target.value)} className="input">
            <option value="">-- Selectionnez --</option>
            {BELGIAN_COURTS.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Arrondissement judiciaire</label>
          <select value={form.arrondissement} onChange={(e) => updateForm("arrondissement", e.target.value)} className="input">
            <option value="">-- Selectionnez --</option>
            {ARRONDISSEMENTS.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Chambre</label>
          <input type="text" value={form.chambre} onChange={(e) => updateForm("chambre", e.target.value)} className="input" placeholder="3eme chambre civile" />
        </div>
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Numero de role</label>
          <input type="text" value={form.court_reference} onChange={(e) => updateForm("court_reference", e.target.value)} className="input" placeholder="2026/1234/A" />
        </div>
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Langue de la procedure</label>
          <select value={form.proc_language} onChange={(e) => updateForm("proc_language", e.target.value)} className="input">
            <option value="fr">Francais</option>
            <option value="nl">Neerlandais</option>
            <option value="de">Allemand</option>
          </select>
        </div>
      </div>
    </div>
  );

  const renderStep5 = () => (
    <div className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Date d'ouverture</label>
          <input type="date" value={form.opened_at} onChange={(e) => updateForm("opened_at", e.target.value)} className="input" />
        </div>
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Date de prescription</label>
          <input type="date" value={form.prescription_date} onChange={(e) => updateForm("prescription_date", e.target.value)} className="input" />
          <p className="text-xs text-neutral-400 mt-1">Date limite pour agir en justice</p>
        </div>
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Prochaine audience</label>
          <div className="flex gap-2">
            <input type="date" value={form.next_hearing_date} onChange={(e) => updateForm("next_hearing_date", e.target.value)} className="input flex-1" />
            <input type="time" value={form.next_hearing_time} onChange={(e) => updateForm("next_hearing_time", e.target.value)} className="input w-28" />
          </div>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-semibold text-neutral-900">Delais importants</label>
          <button type="button" onClick={addDeadline} className="flex items-center gap-1 text-xs text-accent-600 hover:text-accent-700 font-medium">
            <Plus className="w-3.5 h-3.5" /> Ajouter un delai
          </button>
        </div>
        <div className="space-y-2">
          {form.deadlines.map((dl) => (
            <div key={dl.id} className="flex gap-2 items-center bg-neutral-50 p-2 rounded border border-neutral-200">
              <input type="date" value={dl.date} onChange={(e) => updateForm("deadlines", form.deadlines.map((d) => d.id === dl.id ? { ...d, date: e.target.value } : d))} className="input text-sm py-1.5 w-40" />
              <input type="text" placeholder="Description du delai" value={dl.description} onChange={(e) => updateForm("deadlines", form.deadlines.map((d) => d.id === dl.id ? { ...d, description: e.target.value } : d))} className="input text-sm py-1.5 flex-1" />
              <select value={dl.type} onChange={(e) => updateForm("deadlines", form.deadlines.map((d) => d.id === dl.id ? { ...d, type: e.target.value } : d))} className="input text-sm py-1.5 w-36">
                <option value="legal">Legal</option>
                <option value="contractual">Contractuel</option>
                <option value="conventional">Conventionnel</option>
              </select>
              <button type="button" onClick={() => removeDeadline(dl.id)} className="text-neutral-400 hover:text-red-500">
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
          {form.deadlines.length === 0 && <p className="text-xs text-neutral-400 italic">Aucun delai supplementaire</p>}
        </div>
      </div>
    </div>
  );

  const renderStep6 = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-semibold text-neutral-900 mb-3">Type de facturation</label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {BILLING_TYPES.map((bt) => (
            <button
              key={bt.value}
              type="button"
              onClick={() => updateForm("billing_type", bt.value)}
              className={`p-3 rounded-lg border-2 text-left transition-all ${
                form.billing_type === bt.value ? "border-accent bg-accent-50" : "border-neutral-200 hover:border-neutral-300"
              }`}
            >
              <div className={`text-sm font-semibold ${form.billing_type === bt.value ? "text-accent-700" : "text-neutral-700"}`}>{bt.label}</div>
              <div className="text-xs text-neutral-500 mt-0.5">{bt.desc}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {(form.billing_type === "hourly" || form.billing_type === "mixed") && (
          <div>
            <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Taux horaire (EUR)</label>
            <input type="number" value={form.hourly_rate} onChange={(e) => updateForm("hourly_rate", e.target.value)} className="input" min="0" step="5" />
          </div>
        )}
        {(form.billing_type === "forfait" || form.billing_type === "mixed") && (
          <div>
            <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Montant forfaitaire (EUR)</label>
            <input type="number" value={form.fixed_amount} onChange={(e) => updateForm("fixed_amount", e.target.value)} className="input" min="0" />
          </div>
        )}
        {form.billing_type === "success_fee" && (
          <div>
            <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Pourcentage (%)</label>
            <input type="number" value={form.success_fee_pct} onChange={(e) => updateForm("success_fee_pct", e.target.value)} className="input" min="0" max="100" />
          </div>
        )}
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Provision (EUR)</label>
          <input type="number" value={form.provision} onChange={(e) => updateForm("provision", e.target.value)} className="input" min="0" />
        </div>
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1.5">Budget estime (EUR)</label>
          <input type="number" value={form.budget_estimate} onChange={(e) => updateForm("budget_estimate", e.target.value)} className="input" min="0" />
        </div>
      </div>

      {form.billing_type === "pro_deo" && (
        <div className="bg-neutral-50 rounded-lg border border-neutral-200 p-4 space-y-3">
          <h4 className="text-sm font-semibold text-neutral-800">Aide juridique</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-neutral-700 mb-1">Reference BAJ</label>
              <input type="text" value={form.baj_reference} onChange={(e) => updateForm("baj_reference", e.target.value)} className="input" placeholder="Reference du bureau d'aide juridique" />
            </div>
            <div>
              <label className="block text-sm text-neutral-700 mb-1">Type d'aide</label>
              <select value={form.baj_type} onChange={(e) => updateForm("baj_type", e.target.value)} className="input">
                <option value="premiere_ligne">Premiere ligne (consultation)</option>
                <option value="deuxieme_ligne">Deuxieme ligne (designation)</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {form.billing_type !== "pro_deo" && (
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="legal_aid"
            checked={form.legal_aid}
            onChange={(e) => updateForm("legal_aid", e.target.checked)}
            className="w-4 h-4 rounded border-neutral-300 text-accent-600 focus:ring-accent-500"
          />
          <label htmlFor="legal_aid" className="text-sm text-neutral-700">Dossier en aide juridique (partiellement)</label>
        </div>
      )}
    </div>
  );

  const renderStep7 = () => {
    const courtLabel = BELGIAN_COURTS.find((c) => c.value === form.tribunal)?.label;
    const matterLabel = MATTER_TYPES.find((m) => m.value === form.matter_type)?.label;
    const billingLabel = BILLING_TYPES.find((b) => b.value === form.billing_type)?.label;

    return (
      <div className="space-y-6">
        {/* Summary cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-neutral-50 rounded-lg border border-neutral-200 p-4 space-y-2">
            <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Dossier</h4>
            <p className="text-lg font-semibold text-neutral-900">{form.title || "Sans titre"}</p>
            <p className="text-sm text-neutral-600">{form.reference}</p>
            <div className="flex gap-2 flex-wrap">
              <Badge variant="accent" size="sm">{matterLabel}</Badge>
              {form.sub_type && <Badge variant="neutral" size="sm">{SUB_TYPES[form.matter_type]?.find((s) => s.value === form.sub_type)?.label}</Badge>}
              {form.priority !== "normal" && <Badge variant={form.priority === "tres_urgent" ? "danger" : "warning"} size="sm">{form.priority === "tres_urgent" ? "Tres urgent" : "Urgent"}</Badge>}
            </div>
          </div>

          <div className="bg-neutral-50 rounded-lg border border-neutral-200 p-4 space-y-2">
            <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Juridiction</h4>
            <p className="text-sm font-medium text-neutral-800">{courtLabel || "Non definie"}</p>
            {form.arrondissement && <p className="text-sm text-neutral-600">{form.arrondissement}</p>}
            {form.court_reference && <p className="text-sm text-neutral-500">Role : {form.court_reference}</p>}
          </div>

          <div className="bg-neutral-50 rounded-lg border border-neutral-200 p-4 space-y-2">
            <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Parties</h4>
            {form.clients.length > 0 && <p className="text-sm"><span className="text-success-600 font-medium">Clients :</span> {form.clients.map((c) => c.name).join(", ")}</p>}
            {form.adverse.length > 0 && <p className="text-sm"><span className="text-red-600 font-medium">Adverse :</span> {form.adverse.map((a) => a.name).join(", ")}</p>}
            {form.clients.length === 0 && form.adverse.length === 0 && <p className="text-sm text-neutral-400 italic">Aucune partie definie</p>}
          </div>

          <div className="bg-neutral-50 rounded-lg border border-neutral-200 p-4 space-y-2">
            <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Facturation</h4>
            <p className="text-sm font-medium text-neutral-800">{billingLabel}</p>
            {form.hourly_rate && (form.billing_type === "hourly" || form.billing_type === "mixed") && <p className="text-sm text-neutral-600">{form.hourly_rate} EUR/h</p>}
            {form.provision && <p className="text-sm text-neutral-600">Provision : {form.provision} EUR</p>}
          </div>
        </div>

        {form.description && (
          <div className="bg-neutral-50 rounded-lg border border-neutral-200 p-4">
            <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">Resume des faits</h4>
            <p className="text-sm text-neutral-700 whitespace-pre-wrap">{form.description}</p>
          </div>
        )}

        {/* AI Analysis */}
        <div className="bg-white rounded-lg border-2 border-accent-100 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-accent-600" />
              <h3 className="text-base font-semibold text-neutral-900">Analyse IA</h3>
            </div>
            <Button variant="secondary" size="sm" onClick={fetchAiAssist} loading={aiLoading} disabled={aiLoading || !form.matter_type}>
              {aiData ? "Actualiser" : "Analyser avec l'IA"}
            </Button>
          </div>

          {aiLoading && (
            <div className="flex items-center gap-2 text-sm text-neutral-500">
              <Loader2 className="w-4 h-4 animate-spin" /> Analyse en cours...
            </div>
          )}

          {aiData && !aiLoading && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-3">
                <div>
                  <h5 className="text-xs font-semibold text-neutral-500 uppercase mb-1">Juridiction suggeree</h5>
                  <p className="text-sm font-medium text-neutral-800">{aiData.suggested_jurisdiction}</p>
                </div>
                <div>
                  <h5 className="text-xs font-semibold text-neutral-500 uppercase mb-1">Complexite estimee</h5>
                  <Badge variant={aiData.estimated_complexity === "complex" ? "warning" : aiData.estimated_complexity === "simple" ? "success" : "accent"} size="sm">
                    {aiData.estimated_complexity === "complex" ? "Complexe" : aiData.estimated_complexity === "simple" ? "Simple" : "Moderee"}
                  </Badge>
                </div>
                <div>
                  <h5 className="text-xs font-semibold text-neutral-500 uppercase mb-1">Delais legaux</h5>
                  <ul className="space-y-1">
                    {aiData.applicable_deadlines.map((d, i) => (
                      <li key={i} className="text-sm text-neutral-700 flex items-start gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-warning-500 mt-0.5 flex-shrink-0" />
                        <span><strong>{d.name}</strong> : {d.duration} - {d.description}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <h5 className="text-xs font-semibold text-neutral-500 uppercase mb-1">Documents a preparer</h5>
                  <ul className="space-y-1">
                    {aiData.required_documents.map((d, i) => (
                      <li key={i} className="text-sm text-neutral-700 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-accent-500 flex-shrink-0" />
                        {d}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h5 className="text-xs font-semibold text-neutral-500 uppercase mb-1">Points de vigilance</h5>
                  <ul className="space-y-1">
                    {aiData.risk_points.map((r, i) => (
                      <li key={i} className="text-sm text-neutral-700 flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 text-warning-500 flex-shrink-0" />
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="md:col-span-2">
                <h5 className="text-xs font-semibold text-neutral-500 uppercase mb-1">Notes strategiques</h5>
                <p className="text-sm text-neutral-700">{aiData.strategy_notes}</p>
              </div>

              {aiData.belgian_legal_references.length > 0 && (
                <div className="md:col-span-2">
                  <h5 className="text-xs font-semibold text-neutral-500 uppercase mb-1">References juridiques</h5>
                  <div className="flex flex-wrap gap-1.5">
                    {aiData.belgian_legal_references.map((ref, i) => (
                      <span key={i} className="bg-neutral-100 text-neutral-700 text-xs px-2 py-0.5 rounded">{ref}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">{error}</div>
        )}
      </div>
    );
  };

  /* ──────────────────── MAIN RENDER ──────────────────── */

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Back button */}
      <button
        type="button"
        onClick={() => router.push("/dashboard/cases")}
        className="flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-700 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Retour aux dossiers
      </button>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-neutral-900">Nouveau dossier</h1>
        <p className="text-sm text-neutral-500 mt-1">Creez un dossier complet avec toutes les informations necessaires</p>
      </div>

      {/* Step indicator */}
      <div className="bg-white rounded-lg border border-neutral-200 p-4">
        <div className="flex items-center justify-between">
          {STEPS.map((s, i) => (
            <div key={s.num} className="flex items-center">
              <button
                type="button"
                onClick={() => { if (s.num < step || canNext()) setStep(s.num); }}
                className={`flex items-center gap-2 ${s.num <= step ? "cursor-pointer" : "cursor-default"}`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
                  s.num === step ? "bg-accent text-white" : s.num < step ? "bg-success-100 text-success-700" : "bg-neutral-100 text-neutral-400"
                }`}>
                  {s.num < step ? <Check className="w-4 h-4" /> : s.num}
                </div>
                <span className={`text-sm font-medium hidden md:inline ${
                  s.num === step ? "text-accent-700" : s.num < step ? "text-neutral-700" : "text-neutral-400"
                }`}>
                  {s.label}
                </span>
              </button>
              {i < STEPS.length - 1 && (
                <div className={`w-8 lg:w-16 h-0.5 mx-2 ${s.num < step ? "bg-success-300" : "bg-neutral-200"}`} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step content */}
      <div className="bg-white rounded-lg border border-neutral-200 p-6 min-h-[400px]">
        <h2 className="text-lg font-semibold text-neutral-900 mb-5">
          {STEPS[step - 1]?.label === "Type" && "Type de dossier"}
          {STEPS[step - 1]?.label === "Identification" && "Identification du dossier"}
          {STEPS[step - 1]?.label === "Parties" && "Parties au litige"}
          {STEPS[step - 1]?.label === "Juridiction" && "Juridiction et procedure"}
          {STEPS[step - 1]?.label === "Dates" && "Dates cles et delais"}
          {STEPS[step - 1]?.label === "Finances" && "Aspects financiers"}
          {STEPS[step - 1]?.label === "Validation" && "Resume et validation"}
        </h2>

        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
        {step === 4 && renderStep4()}
        {step === 5 && renderStep5()}
        {step === 6 && renderStep6()}
        {step === 7 && renderStep7()}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button
          variant="secondary"
          size="md"
          onClick={() => setStep((s) => Math.max(1, s - 1))}
          disabled={step === 1}
        >
          <ArrowLeft className="w-4 h-4 mr-1" /> Precedent
        </Button>

        {step < 7 ? (
          <Button
            variant="primary"
            size="md"
            onClick={() => setStep((s) => Math.min(7, s + 1))}
            disabled={!canNext()}
          >
            Suivant <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
        ) : (
          <Button
            variant="primary"
            size="lg"
            onClick={handleSubmit}
            loading={creating}
            disabled={creating || !form.title.trim() || !form.matter_type}
          >
            <Check className="w-5 h-5 mr-1" /> Creer le dossier
          </Button>
        )}
      </div>
    </div>
  );
}
