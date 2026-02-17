"use client";

import { useState, useEffect, useRef } from "react";
import { Play, Square, RotateCcw } from "lucide-react";

interface TimerWidgetProps {
  onTimeUpdate?: (seconds: number) => void;
  variant?: "floating" | "inline";
}

interface TimerState {
  isActive: boolean;
  elapsedSeconds: number;
  startTime: number | null;
}

const STORAGE_KEY = "lexibel_timer_state";

export default function TimerWidget({
  onTimeUpdate,
  variant = "inline",
}: TimerWidgetProps) {
  const [timerState, setTimerState] = useState<TimerState>({
    isActive: false,
    elapsedSeconds: 0,
    startTime: null,
  });

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load timer state from localStorage on mount
  useEffect(() => {
    const savedState = localStorage.getItem(STORAGE_KEY);
    if (savedState) {
      try {
        const parsed: TimerState = JSON.parse(savedState);
        // If timer was active, recalculate elapsed time
        if (parsed.isActive && parsed.startTime) {
          const elapsed = Math.floor((Date.now() - parsed.startTime) / 1000);
          setTimerState({
            isActive: true,
            elapsedSeconds: parsed.elapsedSeconds + elapsed,
            startTime: Date.now(),
          });
        } else {
          setTimerState(parsed);
        }
      } catch (e) {
        console.error("Failed to parse timer state:", e);
      }
    }
  }, []);

  // Save timer state to localStorage every 5 seconds when active
  useEffect(() => {
    if (timerState.isActive) {
      const saveTimer = () => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(timerState));
      };

      saveTimerRef.current = setInterval(saveTimer, 5000);
      return () => {
        if (saveTimerRef.current) clearInterval(saveTimerRef.current);
      };
    }
  }, [timerState]);

  // Update timer every second when active
  useEffect(() => {
    if (timerState.isActive && timerState.startTime) {
      intervalRef.current = setInterval(() => {
        setTimerState((prev) => {
          const newElapsed = prev.elapsedSeconds + 1;
          onTimeUpdate?.(newElapsed);
          return {
            ...prev,
            elapsedSeconds: newElapsed,
          };
        });
      }, 1000);

      return () => {
        if (intervalRef.current) clearInterval(intervalRef.current);
      };
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
  }, [timerState.isActive, timerState.startTime, onTimeUpdate]);

  const formatTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const handleStart = () => {
    setTimerState((prev) => ({
      ...prev,
      isActive: true,
      startTime: Date.now(),
    }));
  };

  const handleStop = () => {
    setTimerState((prev) => {
      const newState = {
        ...prev,
        isActive: false,
        startTime: null,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newState));
      return newState;
    });
  };

  const handleReset = () => {
    setTimerState({
      isActive: false,
      elapsedSeconds: 0,
      startTime: null,
    });
    localStorage.removeItem(STORAGE_KEY);
    onTimeUpdate?.(0);
  };

  if (variant === "floating") {
    return (
      <div
        className={`fixed bottom-6 right-6 z-40 bg-white rounded-lg shadow-lg border-2 transition-all duration-300 ${
          timerState.isActive
            ? "border-success-500 animate-pulse-slow"
            : "border-neutral-200"
        }`}
      >
        <div className="p-4">
          {/* Pulsing indicator */}
          {timerState.isActive && (
            <div className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-success-500 rounded-full animate-ping" />
          )}
          {timerState.isActive && (
            <div className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-success-500 rounded-full" />
          )}

          {/* Timer display */}
          <div className="text-2xl font-mono font-bold text-neutral-900 mb-3 tracking-wider min-w-[140px] text-center md:text-3xl md:min-w-[180px]">
            {formatTime(timerState.elapsedSeconds)}
          </div>

          {/* Controls */}
          <div className="flex gap-2 justify-center">
            {!timerState.isActive ? (
              <button
                onClick={handleStart}
                className="bg-success-500 hover:bg-success-600 text-white p-2 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-success-300"
                aria-label="Start timer"
              >
                <Play className="w-4 h-4 md:w-5 md:h-5" />
              </button>
            ) : (
              <button
                onClick={handleStop}
                className="bg-danger-500 hover:bg-danger-600 text-white p-2 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-danger-300"
                aria-label="Stop timer"
              >
                <Square className="w-4 h-4 md:w-5 md:h-5" />
              </button>
            )}
            <button
              onClick={handleReset}
              className="bg-neutral-400 hover:bg-neutral-500 text-white p-2 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-neutral-300"
              aria-label="Reset timer"
            >
              <RotateCcw className="w-4 h-4 md:w-5 md:h-5" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Inline variant
  return (
    <div
      className={`inline-flex items-center gap-3 bg-white rounded-md px-3 py-2 border transition-all duration-200 ${
        timerState.isActive
          ? "border-success-500 shadow-sm"
          : "border-neutral-200"
      }`}
    >
      {/* Pulsing indicator */}
      {timerState.isActive && (
        <div className="relative">
          <div className="w-2 h-2 bg-success-500 rounded-full animate-ping absolute" />
          <div className="w-2 h-2 bg-success-500 rounded-full" />
        </div>
      )}

      {/* Timer display */}
      <div className="text-lg font-mono font-semibold text-neutral-900 tracking-wide min-w-[100px]">
        {formatTime(timerState.elapsedSeconds)}
      </div>

      {/* Controls */}
      <div className="flex gap-1.5">
        {!timerState.isActive ? (
          <button
            onClick={handleStart}
            className="bg-success-500 hover:bg-success-600 text-white p-1.5 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-success-300"
            aria-label="Start timer"
          >
            <Play className="w-3.5 h-3.5" />
          </button>
        ) : (
          <button
            onClick={handleStop}
            className="bg-danger-500 hover:bg-danger-600 text-white p-1.5 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-danger-300"
            aria-label="Stop timer"
          >
            <Square className="w-3.5 h-3.5" />
          </button>
        )}
        <button
          onClick={handleReset}
          className="bg-neutral-400 hover:bg-neutral-500 text-white p-1.5 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-neutral-300"
          aria-label="Reset timer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
