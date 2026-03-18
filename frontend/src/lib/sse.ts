/** A single Server-Sent Event parsed from the stream. */
export interface SSEEvent {
  /** Event type (defaults to "message") */
  event: string;
  /** Event payload data */
  data: string;
}

/**
 * Parse a ReadableStream of SSE bytes into individual SSEEvent objects.
 * Handles multi-line data fields and custom event types per the SSE spec.
 * @param reader - A ReadableStreamDefaultReader providing raw SSE bytes
 * @returns Async generator yielding parsed SSEEvent objects
 */
export async function* parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
): AsyncGenerator<SSEEvent, void, unknown> {
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = 'message';
  let dataLines: string[] = [];

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          dataLines.push(line.slice(6));
        } else if (line === '') {
          if (dataLines.length > 0) {
            yield { event: currentEvent, data: dataLines.join('\n') };
            dataLines = [];
            currentEvent = 'message';
          }
        }
      }
    }

    if (dataLines.length > 0) {
      yield { event: currentEvent, data: dataLines.join('\n') };
    }
  } finally {
    reader.releaseLock();
  }
}
