import type { ChatMessage } from '@/types';

/**
 * Format chat messages as Markdown with User/Assistant headers separated by horizontal rules.
 * @param messages - The chat messages to export
 * @returns Markdown-formatted string
 */
export function exportAsMarkdown(messages: ChatMessage[]): string {
  return messages
    .map((msg) => {
      const header = msg.role === 'user' ? '## User' : '## Assistant';
      return `${header}\n\n${msg.content}`;
    })
    .join('\n\n---\n\n');
}

/**
 * Format chat messages as pretty-printed JSON.
 * @param messages - The chat messages to export
 * @returns JSON string with 2-space indentation
 */
export function exportAsJSON(messages: ChatMessage[]): string {
  return JSON.stringify(messages, null, 2);
}

/**
 * Trigger a file download in the browser by creating a temporary anchor element.
 * @param content - The file content as a string
 * @param filename - The suggested download filename
 * @param mimeType - The MIME type for the Blob (e.g., "text/markdown")
 */
export function downloadFile(
  content: string,
  filename: string,
  mimeType: string,
): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
