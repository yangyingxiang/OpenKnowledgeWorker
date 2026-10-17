import { describe, expect, it } from 'vitest';
import { collectTextDelta, isTerminalEvent, parseSSEBuffer } from './sse';

describe('parseSSEBuffer', () => {
  it('parses complete data lines and keeps the trailing partial line', () => {
    const { events, rest } = parseSSEBuffer(
      'data: {"type":"delta","text":"Hi"}\n\ndata: {"type":"status"}\ndata: {"type":"do',
    );
    expect(events).toEqual([{ type: 'delta', text: 'Hi' }, { type: 'status' }]);
    expect(rest).toBe('data: {"type":"do');
  });

  it('reassembles an event split across chunks', () => {
    const first = parseSSEBuffer('data: {"type":"do');
    expect(first.events).toEqual([]);
    const second = parseSSEBuffer(first.rest + 'ne"}\n');
    expect(second.events).toEqual([{ type: 'done' }]);
    expect(second.rest).toBe('');
  });

  it('skips comments, other fields, malformed JSON and non-object payloads', () => {
    const { events } = parseSSEBuffer(
      ': keep-alive\nevent: message\ndata: {not json}\ndata: 42\ndata: null\ndata: {"type":"ok"}\n',
    );
    expect(events).toEqual([{ type: 'ok' }]);
  });
});

describe('parseSSEBuffer job sequence ids', () => {
  it('attaches the preceding id line as _seq', () => {
    const { events } = parseSSEBuffer(
      'id: 0\ndata: {"type":"job","job_id":"j1"}\n\nid: 1\ndata: {"type":"delta"}\n\n',
    );
    expect(events).toEqual([
      { type: 'job', job_id: 'j1', _seq: 0 },
      { type: 'delta', _seq: 1 },
    ]);
  });

  it('carries an id across chunk boundaries', () => {
    const first = parseSSEBuffer('id: 7\n');
    expect(first.pendingId).toBe(7);
    const second = parseSSEBuffer('data: {"type":"done"}\n', first.pendingId);
    expect(second.events).toEqual([{ type: 'done', _seq: 7 }]);
  });
});

describe('isTerminalEvent / collectTextDelta', () => {
  it('recognises stream-ending events', () => {
    expect(isTerminalEvent({ type: 'done' })).toBe(true);
    expect(isTerminalEvent({ type: 'all_done' })).toBe(true);
    expect(isTerminalEvent({ type: 'error' })).toBe(true);
    expect(isTerminalEvent({ type: 'delta' })).toBe(false);
  });

  it('concatenates only string delta text', () => {
    expect(
      collectTextDelta([
        { type: 'delta', text: 'a' },
        { type: 'status', text: 'ignored' },
        { type: 'delta', text: 5 },
        { type: 'delta', text: 'b' },
      ]),
    ).toBe('ab');
  });
});
