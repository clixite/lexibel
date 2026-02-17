/**
 * CallTimelineItem — Timeline entry for Ringover calls
 *
 * Displays:
 * - Call metadata (direction, duration, contact)
 * - Recording player (if available)
 * - AI insights (transcript, summary, sentiment)
 * - Quick actions (link to case, create task)
 */

'use client';

import { useState } from 'react';
import { Phone, PhoneMissed, Voicemail, ChevronDown, ChevronUp } from 'lucide-react';
import { CallPlayer } from '../calls/CallPlayer';

interface CallTimelineItemProps {
  event: {
    id: string;
    title: string;
    occurred_at: string;
    metadata: {
      direction: 'inbound' | 'outbound';
      call_type: 'answered' | 'missed' | 'voicemail';
      duration_seconds: number;
      caller_number: string;
      callee_number: string;
      recording_url?: string;
      contact_id?: string;
      transcript?: string;
      ai_summary?: string;
      sentiment_score?: number;
      tasks_generated?: boolean;
    };
  };
  contactName?: string;
}

export function CallTimelineItem({ event, contactName }: CallTimelineItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const { metadata } = event;

  // Determine display phone number
  const displayPhone =
    metadata.direction === 'inbound' ? metadata.caller_number : metadata.callee_number;

  // Get call icon
  const getIcon = () => {
    switch (metadata.call_type) {
      case 'answered':
        return <Phone className="w-5 h-5 text-green-600" />;
      case 'missed':
        return <PhoneMissed className="w-5 h-5 text-red-600" />;
      case 'voicemail':
        return <Voicemail className="w-5 h-5 text-blue-600" />;
      default:
        return <Phone className="w-5 h-5 text-gray-600" />;
    }
  };

  // Format duration
  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  // Get sentiment label
  const getSentiment = (): 'positive' | 'neutral' | 'negative' | undefined => {
    if (metadata.sentiment_score === undefined) return undefined;
    if (metadata.sentiment_score < -0.3) return 'negative';
    if (metadata.sentiment_score > 0.3) return 'positive';
    return 'neutral';
  };

  // Format timestamp
  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    return new Intl.DateTimeFormat('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  return (
    <div className="flex gap-3 group">
      {/* Icon */}
      <div className="flex-shrink-0">{getIcon()}</div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900">
              {contactName || displayPhone}
            </p>
            <p className="text-xs text-gray-500">
              {metadata.direction === 'inbound' ? 'Appel entrant' : 'Appel sortant'} •{' '}
              {formatDuration(metadata.duration_seconds)} • {formatTime(event.occurred_at)}
            </p>
          </div>

          {/* Expand button */}
          {metadata.recording_url && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          )}
        </div>

        {/* AI Badges */}
        {(metadata.ai_summary || metadata.transcript || metadata.tasks_generated) && (
          <div className="flex gap-1 mt-2">
            {metadata.transcript && (
              <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-800 rounded">
                Transcrit
              </span>
            )}
            {metadata.ai_summary && (
              <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                Résumé AI
              </span>
            )}
            {metadata.tasks_generated && (
              <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 rounded">
                Tâches créées
              </span>
            )}
          </div>
        )}

        {/* Expanded: Call Player */}
        {isExpanded && metadata.recording_url && (
          <div className="mt-3">
            <CallPlayer
              recordingUrl={metadata.recording_url}
              duration={metadata.duration_seconds}
              transcript={metadata.transcript}
              sentiment={getSentiment()}
              aiSummary={metadata.ai_summary}
              callType={metadata.call_type}
              contactName={contactName}
            />
          </div>
        )}
      </div>
    </div>
  );
}
