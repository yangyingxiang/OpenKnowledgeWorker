/**
 * Pure parsing helpers for the backend's Server-Sent Events streams.
 *
 * The backend emits one JSON object per `data: ` line, e.g.
 *   data: {"type": "delta", "text": "Hello"}
 * Streams finish with a `done`, `all_done` or `error` event.
 */

export interface SSEEvent {
  type: string;
  [key: string]: unknown;
}

/** Event types after which the backend closes the stream. */
const TERMINAL_EVENT_TYPES = new Set(['done', 'all_done', 'error']);

/**
 * Parse all complete lines in `buffer`. The trailing partial line (if any) is returned as
 * `rest` and should be prepended to the next chunk. Non-`data:` lines, malformed JSON and
 * non-object payloads are skipped.
 */
export function parseSSEBuffer(
  buffer: string,
  pendingId: number | null = null,
): { events: SSEEvent[]; rest: string; pendingId: number | null } {
  const lines = buffer.split('\n');
  const rest = lines.pop() || '';
  const events: SSEEvent[] = [];

  for (const line of lines) {
    if (line.startsWith('id: ')) {
      // Background-job streams number their events; `_seq` lets clients resume.
      const id = Number(line.slice(4));
      pendingId = Number.isFinite(id) ? id : null;
    } else if (line.startsWith('data: ')) {
      try {
        const data = JSON.parse(line.slice(6));
        if (data && typeof data === 'object') {
          if (pendingId !== null) (data as SSEEvent)._seq = pendingId;
          events.push(data as SSEEvent);
        }
      } catch {
        // Skip malformed JSON
      }
      pendingId = null;
    }
  }
  return { events, rest, pendingId };
}

export function isTerminalEvent(event: SSEEvent): boolean {
  return TERMINAL_EVENT_TYPES.has(event.type);
}

/** Concatenate the text of all `delta` events (streamed assistant text). */
export function collectTextDelta(events: SSEEvent[]): string {
  let text = '';
  for (const e of events) {
    if (e.type === 'delta' && typeof e.text === 'string') text += e.text;
  }
  return text;
}
