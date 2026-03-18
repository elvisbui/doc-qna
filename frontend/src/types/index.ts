/** Processing state of an uploaded document. */
export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'error';

/** Represents an uploaded document and its processing metadata. */
export interface Document {
  id: string;
  filename: string;
  fileType: string;
  fileSize: number;
  status: DocumentStatus;
  createdAt: string;
  errorMessage?: string;
}

/** A source citation referencing a specific chunk from a retrieved document. */
export interface Citation {
  documentId: string;
  documentName: string;
  chunkContent: string;
  chunkIndex: number;
  relevanceScore: number;
}

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface UploadResponse {
  documentId: string;
  filename: string;
  status: DocumentStatus;
}

export interface DocumentPreview {
  content: string;
  truncated: boolean;
  totalLength: number;
}
