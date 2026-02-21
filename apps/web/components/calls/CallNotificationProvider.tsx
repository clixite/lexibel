/**
 * CallNotificationProvider — Real-time call notifications via SSE
 *
 * 2026 Best Practices:
 * - Uses useEventStream hook for SSE connection
 * - Toast notifications for incoming calls
 * - Auto-refresh timeline on new events
 * - Optimistic UI updates
 * - Error handling and reconnection
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner'; // Modern toast library (shadcn/ui)
import { Phone, PhoneMissed, Voicemail } from 'lucide-react';

import { useEventStream } from '@/lib/hooks/useEventStream';

interface CallNotificationProviderProps {
  children: React.ReactNode;
}

export function CallNotificationProvider({ children }: CallNotificationProviderProps) {
  const router = useRouter();

  const { isConnected, isReconnecting } = useEventStream({
    // Handle incoming call events
    onCallEvent: (data) => {
      // Build notification message
      const contactName = data.contact_name || data.phone_number;
      const direction = data.direction === 'inbound' ? 'entrant' : 'sortant';

      // Choose icon and message based on call type
      let icon;
      let message;

      switch (data.call_type) {
        case 'answered':
          icon = <Phone className="text-green-600" />;
          message = `Appel ${direction} avec ${contactName}`;
          break;
        case 'missed':
          icon = <PhoneMissed className="text-red-600" />;
          message = `Appel manqué de ${contactName}`;
          break;
        case 'voicemail':
          icon = <Voicemail className="text-blue-600" />;
          message = `Nouveau message vocal de ${contactName}`;
          break;
        default:
          icon = <Phone />;
          message = `Appel ${direction} - ${contactName}`;
      }

      // Show toast notification
      toast(message, {
        icon,
        description: data.has_recording
          ? 'Enregistrement disponible'
          : `Durée: ${formatDuration(data.duration_seconds)}`,
        action: data.case_id
          ? {
              label: 'Voir le dossier',
              onClick: () => router.push(`/dashboard/cases/${data.case_id}`),
            }
          : undefined,
        duration: 5000,
      });

      // Trigger timeline refresh if we're on a case page
      if (data.case_id) {
        // Use Next.js router refresh to trigger server component re-render
        router.refresh();
      }
    },

    // Handle AI processing completion
    onCallAiCompleted: (data) => {
      const features = [];
      if (data.has_transcript) features.push('Transcription');
      if (data.has_summary) features.push('Résumé');
      if (data.sentiment_score !== undefined) features.push('Sentiment');
      if (data.tasks_generated) features.push('Tâches');

      if (features.length > 0) {
        toast.success('Analyse AI terminée', {
          description: features.join(' • '),
          duration: 4000,
        });

        // Refresh to show new AI insights
        router.refresh();
      }
    },

    // Handle other events
    onCaseUpdated: () => {
      router.refresh();
    },

    onInboxItem: () => {
      toast.info('Nouvel élément dans la boîte de réception', {
        duration: 3000,
      });
    },
  });

  // Show connection status
  useEffect(() => {
    if (isReconnecting) {
      toast.loading('Reconnexion au serveur...', {
        id: 'sse-reconnecting',
      });
    } else if (isConnected) {
      toast.dismiss('sse-reconnecting');
    }
  }, [isConnected, isReconnecting]);

  return <>{children}</>;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  }

  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs}s`;
}
