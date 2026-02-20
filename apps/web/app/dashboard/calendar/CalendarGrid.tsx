"use client";

import { useMemo } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui";

interface CalendarEvent {
  id: string;
  title: string;
  start_time: string;
  date: string;
  time: string;
  location?: string;
}

interface Deadline {
  title: string;
  date: string;
  days_remaining: number;
  urgency: "critical" | "urgent" | "attention" | "normal";
  case_id: string | null;
  case_title: string | null;
}

interface Props {
  events: CalendarEvent[];
  deadlines: Deadline[];
  currentMonth: Date;
  onMonthChange: (d: Date) => void;
  onDayClick: (date: string) => void;
}

const DAYS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
const MONTHS_FR = [
  "Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin",
  "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre",
];

function toISO(d: Date): string {
  return d.toISOString().split("T")[0];
}

export default function CalendarGrid({ events, deadlines, currentMonth, onMonthChange, onDayClick }: Props) {
  const today = toISO(new Date());

  const calendarDays = useMemo(() => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    // Monday = 0
    let startPad = firstDay.getDay() - 1;
    if (startPad < 0) startPad = 6;

    const days: { date: string; inMonth: boolean; day: number }[] = [];

    // Previous month padding
    for (let i = startPad - 1; i >= 0; i--) {
      const d = new Date(year, month, -i);
      days.push({ date: toISO(d), inMonth: false, day: d.getDate() });
    }

    // Current month
    for (let d = 1; d <= lastDay.getDate(); d++) {
      const dt = new Date(year, month, d);
      days.push({ date: toISO(dt), inMonth: true, day: d });
    }

    // Next month padding (fill to 42 = 6 rows)
    while (days.length < 42) {
      const d = new Date(year, month + 1, days.length - lastDay.getDate() - startPad + 1);
      days.push({ date: toISO(d), inMonth: false, day: d.getDate() });
    }

    return days;
  }, [currentMonth]);

  // Map events and deadlines by date
  const eventsByDate = useMemo(() => {
    const map: Record<string, CalendarEvent[]> = {};
    events.forEach((e) => {
      const d = e.date || e.start_time?.split("T")[0];
      if (d) {
        if (!map[d]) map[d] = [];
        map[d].push(e);
      }
    });
    return map;
  }, [events]);

  const deadlinesByDate = useMemo(() => {
    const map: Record<string, Deadline[]> = {};
    deadlines.forEach((dl) => {
      if (!map[dl.date]) map[dl.date] = [];
      map[dl.date].push(dl);
    });
    return map;
  }, [deadlines]);

  const prevMonth = () => {
    const d = new Date(currentMonth);
    d.setMonth(d.getMonth() - 1);
    onMonthChange(d);
  };

  const nextMonth = () => {
    const d = new Date(currentMonth);
    d.setMonth(d.getMonth() + 1);
    onMonthChange(d);
  };

  const urgencyBorder = (urgency: string) => {
    switch (urgency) {
      case "critical": return "ring-2 ring-red-400";
      case "urgent": return "ring-2 ring-amber-400";
      case "attention": return "ring-1 ring-yellow-400";
      default: return "";
    }
  };

  return (
    <div className="bg-white rounded-lg border border-neutral-200 overflow-hidden">
      {/* Month header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <button onClick={prevMonth} className="p-1.5 rounded hover:bg-neutral-100 text-neutral-600">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <h3 className="text-lg font-semibold text-neutral-900">
          {MONTHS_FR[currentMonth.getMonth()]} {currentMonth.getFullYear()}
        </h3>
        <button onClick={nextMonth} className="p-1.5 rounded hover:bg-neutral-100 text-neutral-600">
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Day names */}
      <div className="grid grid-cols-7 border-b border-neutral-200">
        {DAYS.map((d) => (
          <div key={d} className="px-2 py-2 text-center text-xs font-semibold text-neutral-500 uppercase">
            {d}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7">
        {calendarDays.map((cell, idx) => {
          const dayEvents = eventsByDate[cell.date] || [];
          const dayDeadlines = deadlinesByDate[cell.date] || [];
          const isToday = cell.date === today;
          const hasDeadline = dayDeadlines.length > 0;
          const worstUrgency = dayDeadlines[0]?.urgency;

          return (
            <button
              key={idx}
              type="button"
              onClick={() => onDayClick(cell.date)}
              className={`min-h-[80px] p-1.5 border-b border-r border-neutral-100 text-left transition-colors hover:bg-neutral-50 ${
                !cell.inMonth ? "bg-neutral-50" : ""
              } ${hasDeadline ? urgencyBorder(worstUrgency) : ""}`}
            >
              <div className={`text-sm font-medium mb-1 ${
                isToday
                  ? "w-6 h-6 rounded-full bg-accent text-white flex items-center justify-center text-xs"
                  : cell.inMonth
                    ? "text-neutral-800"
                    : "text-neutral-300"
              }`}>
                {cell.day}
              </div>

              <div className="space-y-0.5">
                {dayEvents.slice(0, 2).map((ev, i) => (
                  <div key={i} className="text-[10px] leading-tight px-1 py-0.5 rounded bg-accent-50 text-accent-700 truncate">
                    {ev.time && <span className="font-medium">{ev.time} </span>}
                    {ev.title}
                  </div>
                ))}
                {dayDeadlines.slice(0, 1).map((dl, i) => (
                  <div key={`dl-${i}`} className={`text-[10px] leading-tight px-1 py-0.5 rounded truncate ${
                    dl.urgency === "critical" ? "bg-red-100 text-red-700" : "bg-amber-50 text-amber-700"
                  }`}>
                    {dl.title}
                  </div>
                ))}
                {(dayEvents.length + dayDeadlines.length > 3) && (
                  <div className="text-[10px] text-neutral-400">
                    +{dayEvents.length + dayDeadlines.length - 3} autres
                  </div>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
