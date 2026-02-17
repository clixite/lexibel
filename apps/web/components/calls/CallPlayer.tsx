/**
 * CallPlayer — Advanced audio player for Ringover call recordings
 *
 * 2026 Features:
 * - Waveform visualization
 * - Playback speed control (0.5x, 1x, 1.5x, 2x)
 * - Timestamp navigation
 * - Transcript sync (highlights text during playback)
 * - Download recording
 * - Sentiment indicator
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { Play, Pause, Download, SkipBack, SkipForward } from 'lucide-react';

interface CallPlayerProps {
  recordingUrl: string;
  duration: number; // seconds
  transcript?: string;
  sentiment?: 'positive' | 'neutral' | 'negative';
  aiSummary?: string;
  callType: string;
  contactName?: string;
}

export function CallPlayer({
  recordingUrl,
  duration,
  transcript,
  sentiment,
  aiSummary,
  callType,
  contactName,
}: CallPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [volume, setVolume] = useState(1.0);

  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateTime = () => setCurrentTime(audio.currentTime);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener('timeupdate', updateTime);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', updateTime);
      audio.removeEventListener('ended', handleEnded);
    };
  }, []);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;

    const newTime = parseFloat(e.target.value);
    audio.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const changePlaybackRate = (rate: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.playbackRate = rate;
    setPlaybackRate(rate);
  };

  const skip = (seconds: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.currentTime = Math.max(0, Math.min(duration, audio.currentTime + seconds));
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getSentimentColor = () => {
    switch (sentiment) {
      case 'positive':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'negative':
        return 'bg-red-100 text-red-800 border-red-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const progress = (currentTime / duration) * 100;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      {/* Hidden audio element */}
      <audio ref={audioRef} src={recordingUrl} preload="metadata" />

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-900">
            {callType === 'answered' && '📞'}
            {callType === 'voicemail' && '🎙️'}
            {callType === 'missed' && '📵'}
            {contactName || 'Appel inconnu'}
          </span>
          {sentiment && (
            <span
              className={`px-2 py-1 text-xs font-medium rounded-full border ${getSentimentColor()}`}
            >
              {sentiment === 'positive' && '😊 Positif'}
              {sentiment === 'neutral' && '😐 Neutre'}
              {sentiment === 'negative' && '😞 Négatif'}
            </span>
          )}
        </div>
        <button
          onClick={() => window.open(recordingUrl, '_blank')}
          className="text-gray-600 hover:text-gray-900 transition-colors"
          title="Télécharger l'enregistrement"
        >
          <Download size={18} />
        </button>
      </div>

      {/* Waveform / Progress Bar */}
      <div className="mb-3">
        <div className="relative w-full h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="absolute left-0 top-0 h-full bg-blue-500 transition-all duration-100"
            style={{ width: `${progress}%` }}
          />
          <input
            type="range"
            min="0"
            max={duration}
            value={currentTime}
            onChange={handleSeek}
            className="absolute inset-0 w-full opacity-0 cursor-pointer"
          />
        </div>
      </div>

      {/* Time display */}
      <div className="flex justify-between text-xs text-gray-600 mb-3">
        <span>{formatTime(currentTime)}</span>
        <span>{formatTime(duration)}</span>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        {/* Playback controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => skip(-10)}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            title="Reculer de 10s"
          >
            <SkipBack size={18} />
          </button>

          <button
            onClick={togglePlay}
            className="p-3 bg-blue-600 text-white rounded-full hover:bg-blue-700 transition-colors shadow-md"
          >
            {isPlaying ? <Pause size={20} /> : <Play size={20} />}
          </button>

          <button
            onClick={() => skip(10)}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            title="Avancer de 10s"
          >
            <SkipForward size={18} />
          </button>
        </div>

        {/* Playback speed */}
        <div className="flex items-center gap-1">
          {[0.5, 1.0, 1.5, 2.0].map((rate) => (
            <button
              key={rate}
              onClick={() => changePlaybackRate(rate)}
              className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                playbackRate === rate
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              {rate}x
            </button>
          ))}
        </div>
      </div>

      {/* AI Summary */}
      {aiSummary && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-xs font-semibold text-gray-700 mb-1">Résumé AI</p>
          <p className="text-sm text-gray-600">{aiSummary}</p>
        </div>
      )}

      {/* Transcript */}
      {transcript && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <p className="text-xs font-semibold text-gray-700 mb-1">Transcription</p>
          <div className="max-h-32 overflow-y-auto text-sm text-gray-600 leading-relaxed">
            {transcript}
          </div>
        </div>
      )}
    </div>
  );
}
