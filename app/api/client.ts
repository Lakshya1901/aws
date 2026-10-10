// Typed client for the AnnaSetu API (CLAUDE.md Section 13). The app never calls AWS directly.
import { ApiError } from './errors';
import type {
  ApiErrorBody,
  CropsResponse,
  FetchResponse,
  ImpactResponse,
  PlanRequest,
  PlanResponse,
  RadarCropId,
  RecommendRequest,
  RecommendResponse,
  RescueRequest,
  RescueResponse,
  RiskQuery,
  RiskResponse,
  SpeakRequest,
  SpeakResponse,
  VoiceParseRequest,
  VoiceParseResponse,
  VoiceUploadRequest,
  VoiceUploadResponse,
} from './types';

export { ApiError };

export const MOCK = process.env.EXPO_PUBLIC_API_MOCK === '1';
const BASE_URL = (process.env.EXPO_PUBLIC_API_URL ?? '').replace(/\/+$/, '');
const API_KEY = process.env.EXPO_PUBLIC_API_KEY ?? '';
const TIMEOUT_MS = 20000;

/** Today's live mandi prices, or the saved demo glut day (Settings, D34); sent with every request. */
export type DataMode = 'live' | 'demo';
let dataMode: DataMode = 'live';
export const setDataMode = (m: DataMode) => {
  dataMode = m;
};
export const getDataMode = () => dataMode;

// Loaded only in mock mode so real mode never touches fixtures.
const mock: typeof import('./mock').mock | null = MOCK ? require('./mock').mock : null;

async function request<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
  if (!BASE_URL) throw new ApiError(0, 'no_api_url', 'EXPO_PUBLIC_API_URL is not set');
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(BASE_URL + path, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'x-annasetu-data': dataMode,
        ...(API_KEY ? { 'x-api-key': API_KEY } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: ctrl.signal,
    });
  } catch {
    throw new ApiError(0, 'network');
  } finally {
    clearTimeout(timer);
  }
  const json = (await res.json().catch(() => null)) as unknown;
  if (!res.ok) {
    const err = (json ?? {}) as Partial<ApiErrorBody>;
    throw new ApiError(res.status, err.error ?? `http_${res.status}`, err.message);
  }
  if (json && typeof json === 'object' && '_fixture' in json) {
    // Fixture data must never be shown as real data.
    throw new ApiError(500, 'fixture_in_real_mode');
  }
  return json as T;
}

function qs(params: Record<string, string | number | undefined>): string {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  return parts.length ? `?${parts.join('&')}` : '';
}

export const api = {
  crops(crop?: RadarCropId): Promise<CropsResponse> {
    if (mock) return mock.crops(crop);
    return request('GET', `/crops${qs({ crop })}`);
  },

  /** Queue loading one crop's data; poll crops(crop) until status is ready. */
  fetchCrop(crop: RadarCropId): Promise<FetchResponse> {
    if (mock) return mock.fetchCrop(crop);
    return request('POST', '/crops/fetch', { crop });
  },

  risk(q: RiskQuery): Promise<RiskResponse> {
    if (mock) return mock.risk(q);
    return request('GET', `/risk${qs({ crop: q.crop, state: q.state, lat: q.lat, lon: q.lon })}`);
  },

  voiceUpload(req: VoiceUploadRequest): Promise<VoiceUploadResponse> {
    if (mock) return mock.voiceUpload();
    return request('POST', '/voice/upload', req);
  },

  /** PUT the recorded file to the presigned S3 URL from voiceUpload. */
  async putAudio(uploadUrl: string, fileUri: string, contentType: string): Promise<void> {
    if (mock) return;
    const file = await fetch(fileUri);
    const blob = await file.blob();
    const res = await fetch(uploadUrl, {
      method: 'PUT',
      headers: { 'Content-Type': contentType },
      body: blob,
    });
    if (!res.ok) throw new ApiError(res.status, 'upload_failed');
  },

  voiceParse(req: VoiceParseRequest): Promise<VoiceParseResponse> {
    if (mock) return mock.voiceParse();
    return request('POST', '/voice/parse', req);
  },

  recommend(req: RecommendRequest): Promise<RecommendResponse> {
    if (mock) return mock.recommend(req);
    return request('POST', '/recommend', req);
  },

  /** Unsold stock at a city mandi: the same POST /recommend with source "mandi_unsold". */
  rescue(req: RescueRequest): Promise<RescueResponse> {
    if (mock) return mock.rescue(req);
    return request('POST', '/recommend', req);
  },

  plan(req: PlanRequest): Promise<PlanResponse> {
    if (mock) return mock.plan(req);
    return request('POST', '/plan', req);
  },

  speak(req: SpeakRequest): Promise<SpeakResponse> {
    if (mock) return mock.speak();
    return request('POST', '/speak', req);
  },

  impact(planId: string): Promise<ImpactResponse> {
    if (mock) return mock.impact();
    return request('GET', `/impact${qs({ plan_id: planId })}`);
  },
};
