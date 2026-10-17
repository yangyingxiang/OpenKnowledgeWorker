'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { parseSSEBuffer, isTerminalEvent, collectTextDelta, type SSEEvent } from './sse';
import { api } from './api';

export type { SSEEvent } from './sse';

/** Maximum events kept in state to prevent unbounded memory growth. */
const MAX_EVENTS = 200;

/** How often to re-attach to a background job whose stream dropped, and the delay between tries. */
const MAX_RESUME_ATTEMPTS = 5;
const RESUME_DELAY_MS = 2000;

export function useSSE() {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamText, setStreamText] = useState('');
  const abortRef = useRef<AbortController | null>(null);

  // Abort any running stream when the component using this hook unmounts.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const startStream = useCallback(
    async (fetchFn: () => Promise<Response>, onEvent?: (event: SSEEvent) => void) => {
      // Abort any previous stream before starting a new one.
      abortRef.current?.abort();

      setEvents([]);
      setStreamText('');
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      // Long-running work runs as a background job on the server. If the connection drops
      // before a terminal event, re-attach to the job's event stream where we left off.
      let jobId: string | null = null;
      let lastSeq = -1;
      let finished = false;

      const consume = async (response: Response) => {
        if (!response.ok || !response.body) {
          throw new Error(`Stream failed: ${response.status}`);
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let pendingId: number | null = null;

        while (true) {
          // Check if aborted between reads.
          if (controller.signal.aborted) return;

          const { done, value } = await reader.read();
          if (done) return;

          buffer += decoder.decode(value, { stream: true });

          // Batch: collect all parsed events from this chunk before updating state.
          const parsed = parseSSEBuffer(buffer, pendingId);
          buffer = parsed.rest;
          pendingId = parsed.pendingId;
          const batchedEvents = parsed.events.filter(
            (e) => typeof e._seq !== 'number' || e._seq > lastSeq,
          );
          for (const e of batchedEvents) {
            if (e.type === 'job' && typeof e.job_id === 'string') jobId = e.job_id;
            if (typeof e._seq === 'number') lastSeq = e._seq;
          }
          const textDelta = collectTextDelta(batchedEvents);
          const streamEnded = batchedEvents.some(isTerminalEvent);

          // Single batched state update for events (capped to prevent memory bloat).
          if (batchedEvents.length > 0) {
            setEvents((prev) => {
              const next = [...prev, ...batchedEvents];
              return next.length > MAX_EVENTS ? next.slice(next.length - MAX_EVENTS) : next;
            });
          }

          if (textDelta) {
            setStreamText((prev) => prev + textDelta);
          }

          // Fire callbacks outside of state updates.
          for (const data of batchedEvents) {
            try {
              onEvent?.(data);
            } catch {
              /* prevent callback errors from killing stream */
            }
          }

          if (streamEnded) {
            finished = true;
            setIsStreaming(false);
          }
        }
      };

      try {
        try {
          await consume(await fetchFn());
        } catch (err) {
          if (!jobId || (err as Error).name === 'AbortError') throw err;
        }
        for (let attempt = 0; !finished && jobId && attempt < MAX_RESUME_ATTEMPTS; attempt++) {
          if (controller.signal.aborted) break;
          await new Promise((resolve) => setTimeout(resolve, RESUME_DELAY_MS));
          try {
            await consume(await api.resumeJobEvents(jobId, lastSeq));
          } catch (err) {
            if ((err as Error).name === 'AbortError') throw err;
          }
        }
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          console.error('SSE error:', err);
        }
      } finally {
        setIsStreaming(false);
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
      }
    },
    [],
  );

  const stopStream = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  return { events, isStreaming, streamText, startStream, stopStream, setStreamText };
}
