"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { Button, Modal } from "@/components/ui";

interface NewEvent {
  type: string;
  title: string;
  date: string;
  start_time: string;
  end_time: string;
  location: string;
  case_id: string;
  description: string;
  reminder: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSave: (event: NewEvent) => void;
  cases: { id: string; title: string; reference: string }[];
}

const EVENT_TYPES = [
  { value: "audience", label: "Audience" },
  { value: "rdv", label: "Rendez-vous" },
  { value: "echeance", label: "Echeance" },
  { value: "reunion", label: "Reunion" },
  { value: "autre", label: "Autre" },
];

const REMINDERS = [
  { value: "none", label: "Aucun rappel" },
  { value: "1d", label: "1 jour avant" },
  { value: "3d", label: "3 jours avant" },
  { value: "7d", label: "1 semaine avant" },
];

const BELGIAN_COURTS = [
  "Justice de paix",
  "Tribunal de police",
  "Tribunal de premiere instance",
  "Tribunal de l'entreprise",
  "Tribunal du travail",
  "Cour d'appel de Bruxelles",
  "Cour d'appel de Liege",
  "Cour d'appel de Mons",
  "Cour d'appel d'Anvers",
  "Cour d'appel de Gand",
  "Cour de cassation",
  "Conseil d'Etat",
];

export default function EventCreationModal({ isOpen, onClose, onSave, cases }: Props) {
  const [form, setForm] = useState<NewEvent>({
    type: "rdv",
    title: "",
    date: new Date().toISOString().split("T")[0],
    start_time: "09:00",
    end_time: "10:00",
    location: "",
    case_id: "",
    description: "",
    reminder: "1d",
  });

  const [showCourtSuggestions, setShowCourtSuggestions] = useState(false);

  const update = <K extends keyof NewEvent>(key: K, val: NewEvent[K]) => {
    setForm((f) => ({ ...f, [key]: val }));
  };

  const handleSubmit = () => {
    if (!form.title.trim() || !form.date) return;
    onSave(form);
    setForm({
      type: "rdv",
      title: "",
      date: new Date().toISOString().split("T")[0],
      start_time: "09:00",
      end_time: "10:00",
      location: "",
      case_id: "",
      description: "",
      reminder: "1d",
    });
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Nouvel evenement"
      size="lg"
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="secondary" size="md" onClick={onClose}>Annuler</Button>
          <Button variant="primary" size="md" onClick={handleSubmit} disabled={!form.title.trim()}>Ajouter</Button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Type */}
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-2">Type</label>
          <div className="flex gap-2 flex-wrap">
            {EVENT_TYPES.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => update("type", t.value)}
                className={`px-3 py-1.5 rounded border text-sm font-medium transition-colors ${
                  form.type === t.value
                    ? "bg-accent-50 border-accent text-accent-700"
                    : "border-neutral-200 text-neutral-600 hover:border-neutral-300"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Title */}
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1">Titre</label>
          <input
            type="text"
            value={form.title}
            onChange={(e) => update("title", e.target.value)}
            className="input"
            placeholder="Ex: Audience de plaidoirie"
          />
        </div>

        {/* Date + Times */}
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-sm font-semibold text-neutral-900 mb-1">Date</label>
            <input type="date" value={form.date} onChange={(e) => update("date", e.target.value)} className="input" />
          </div>
          <div>
            <label className="block text-sm font-semibold text-neutral-900 mb-1">Heure debut</label>
            <input type="time" value={form.start_time} onChange={(e) => update("start_time", e.target.value)} className="input" />
          </div>
          <div>
            <label className="block text-sm font-semibold text-neutral-900 mb-1">Heure fin</label>
            <input type="time" value={form.end_time} onChange={(e) => update("end_time", e.target.value)} className="input" />
          </div>
        </div>

        {/* Location */}
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1">Lieu</label>
          <input
            type="text"
            value={form.location}
            onChange={(e) => update("location", e.target.value)}
            onFocus={() => form.type === "audience" && setShowCourtSuggestions(true)}
            onBlur={() => setTimeout(() => setShowCourtSuggestions(false), 200)}
            className="input"
            placeholder={form.type === "audience" ? "Tribunal..." : "Adresse ou visio"}
          />
          {showCourtSuggestions && form.type === "audience" && (
            <div className="mt-1 bg-white border border-neutral-200 rounded shadow-lg max-h-40 overflow-y-auto z-10">
              {BELGIAN_COURTS.filter((c) => c.toLowerCase().includes(form.location.toLowerCase()) || !form.location).map((c) => (
                <button
                  key={c}
                  type="button"
                  onMouseDown={() => { update("location", c); setShowCourtSuggestions(false); }}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-accent-50"
                >
                  {c}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Case link */}
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1">Dossier lie (optionnel)</label>
          <select value={form.case_id} onChange={(e) => update("case_id", e.target.value)} className="input">
            <option value="">-- Aucun --</option>
            {cases.map((c) => (
              <option key={c.id} value={c.id}>{c.reference} - {c.title}</option>
            ))}
          </select>
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1">Description</label>
          <textarea value={form.description} onChange={(e) => update("description", e.target.value)} rows={3} className="input" placeholder="Notes supplementaires..." />
        </div>

        {/* Reminder */}
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-1">Rappel</label>
          <select value={form.reminder} onChange={(e) => update("reminder", e.target.value)} className="input max-w-xs">
            {REMINDERS.map((r) => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>
        </div>
      </div>
    </Modal>
  );
}
