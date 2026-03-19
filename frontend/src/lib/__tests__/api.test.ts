import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  getDocuments,
  uploadDocument,
  deleteDocument,
  ApiError,
} from '../api';

// Mock global fetch
const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('getDocuments', () => {
  it('fetches documents from /api/documents', async () => {
    const mockDocuments = [
      {
        id: '1',
        filename: 'test.pdf',
        fileType: 'pdf',
        fileSize: 1024,
        status: 'ready',
        createdAt: '2026-01-01',
      },
    ];

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ documents: mockDocuments, total: 1 }),
    });

    const result = await getDocuments();

    expect(mockFetch).toHaveBeenCalledWith('/api/documents');
    expect(result).toEqual(mockDocuments);
  });

  it('throws ApiError on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      text: () => Promise.resolve('Something went wrong'),
    });

    await expect(getDocuments()).rejects.toThrow(ApiError);
    await expect(getDocuments()).rejects.toThrow(); // re-mock needed
  });

  it('throws ApiError with status code', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      text: () => Promise.resolve(''),
    });

    try {
      await getDocuments();
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(404);
    }
  });
});

describe('uploadDocument', () => {
  it('sends POST with FormData to /api/documents/upload', async () => {
    const mockResponse = {
      documentId: '123',
      filename: 'test.pdf',
      status: 'pending',
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const file = new File(['content'], 'test.pdf', {
      type: 'application/pdf',
    });
    const result = await uploadDocument(file);

    expect(mockFetch).toHaveBeenCalledWith('/api/documents/upload', {
      method: 'POST',
      body: expect.any(FormData),
    });
    expect(result).toEqual(mockResponse);
  });
});

describe('deleteDocument', () => {
  it('sends DELETE request to /api/documents/:id', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
    });

    await deleteDocument('abc-123');

    expect(mockFetch).toHaveBeenCalledWith('/api/documents/abc-123', {
      method: 'DELETE',
    });
  });

  it('throws ApiError on failure', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      text: () => Promise.resolve('Document not found'),
    });

    try {
      await deleteDocument('bad-id');
      expect.fail('Should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(404);
      expect((err as ApiError).message).toBe('Document not found');
    }
  });
});

describe('ApiError', () => {
  it('has correct name and status properties', () => {
    const error = new ApiError(422, 'Validation failed');

    expect(error.name).toBe('ApiError');
    expect(error.status).toBe(422);
    expect(error.message).toBe('Validation failed');
    expect(error).toBeInstanceOf(Error);
  });
});
