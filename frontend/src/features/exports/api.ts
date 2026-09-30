import { http, parseResponse, authBridge, API_BASE_URL, ApiError, toApiError } from '@/api';
import {
  exportArtifactSchema,
  exportListSchema,
  exportFileExtension,
  type ExportArtifact,
  type ExportKind,
} from './schemas';

/** Resolve a possibly-relative download URL against the API origin. */
function resolveDownloadUrl(url: string): string {
  if (/^https?:\/\//i.test(url)) return url;
  const origin = new URL(API_BASE_URL).origin;
  return new URL(url, origin).toString();
}

/** Programmatically trigger a browser download of a blob (guarded for jsdom). */
function triggerBlobDownload(blob: Blob, filename: string): void {
  if (typeof document === 'undefined' || typeof URL.createObjectURL !== 'function') return;
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.rel = 'noopener';
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(objectUrl);
}

/** Export artifact calls (code-architecture §4 #20-#21). */
export const exportsApi = {
  async list(analysisId: string, signal?: AbortSignal): Promise<ExportArtifact[]> {
    const data = await http.get(`/analyses/${analysisId}/exports/`, {
      ...(signal ? { signal } : {}),
    });
    const parsed = parseResponse(exportListSchema, data);
    return Array.isArray(parsed) ? parsed : parsed.results;
  },

  /** Request a new export; the backend responds 202 + the pending artifact. */
  async create(analysisId: string, kind: ExportKind): Promise<ExportArtifact> {
    const data = await http.post(`/analyses/${analysisId}/exports/`, { body: { kind } });
    return parseResponse(exportArtifactSchema, data);
  },

  async get(exportId: string, signal?: AbortSignal): Promise<ExportArtifact> {
    const data = await http.get(`/exports/${exportId}/`, {
      ...(signal ? { signal } : {}),
    });
    return parseResponse(exportArtifactSchema, data);
  },

  /**
   * Download a ready artifact through the app's auth layer. The download_url
   * (never a raw storage_key) is fetched with the JWT attached so it works for
   * both signed and auth-protected URLs; the response blob is saved client-side.
   */
  async download(artifact: ExportArtifact): Promise<void> {
    if (!artifact.download_url) {
      throw new ApiError({
        code: 'export_not_ready',
        message: 'This export is not ready to download yet.',
        status: 0,
      });
    }
    const url = resolveDownloadUrl(artifact.download_url);
    const headers: Record<string, string> = {};
    const token = authBridge.getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;

    let response: Response;
    try {
      response = await fetch(url, { headers });
    } catch {
      throw toApiError(null, 0);
    }
    if (!response.ok) {
      throw toApiError(null, response.status);
    }
    const blob = await response.blob();
    triggerBlobDownload(blob, `analysis-export.${exportFileExtension(artifact.kind)}`);
  },
};
