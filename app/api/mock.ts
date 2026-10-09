// Mock mode (EXPO_PUBLIC_API_MOCK=1): returns development fixtures. Never used in real mode.
// Every fixture carries "_fixture": true and the UI shows a FIXTURE banner for it.
import { ApiError } from './errors';
import type {
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
  SpeakResponse,
  VoiceParseResponse,
  VoiceUploadResponse,
} from './types';

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

const MOCK_CROPS = ['tomato', 'onion', 'potato', 'banana'];

export const mock = {
  async crops(crop?: RadarCropId): Promise<CropsResponse> {
    await delay(200);
    const all = MOCK_CROPS.map((c) => ({
      crop_id: c,
      name: c[0].toUpperCase() + c.slice(1),
      category: c === 'banana' ? 'Fruits' : 'Vegetables',
      markets: 0,
      preload: true,
      routing: c === 'tomato' || c === 'onion',
      status: 'ready' as const,
    }));
    return { _fixture: true, crops: crop ? all.filter((c) => c.crop_id === crop) : all };
  },
  async fetchCrop(crop: RadarCropId): Promise<FetchResponse> {
    await delay(200);
    return { _fixture: true, crop, status: 'ready' };
  },
  async risk(_q: RiskQuery): Promise<RiskResponse> {
    await delay(400);
    return require('./fixtures/risk.fixture.json') as RiskResponse;
  },
  async voiceUpload(): Promise<VoiceUploadResponse> {
    await delay(200);
    return { _fixture: true, upload_url: 'mock://upload', audio_key: 'fixture/audio.m4a' };
  },
  async voiceParse(): Promise<VoiceParseResponse> {
    await delay(800);
    return require('./fixtures/voice_parse.fixture.json') as VoiceParseResponse;
  },
  // tomato: glut-day recommendation (harvest "tomorrow": price crash with normal arrivals, D10);
  // onion: Second Life states; potato: 422 no markets; banana: 422 crop not set up.
  async recommend(req: RecommendRequest): Promise<RecommendResponse> {
    await delay(600);
    if (req.crop === 'potato') throw new ApiError(422, 'no_markets_in_radius');
    if (req.crop === 'banana') throw new ApiError(422, 'crop_not_configured');
    const base =
      req.crop !== 'tomato'
        ? (require('./fixtures/recommend_second_life.fixture.json') as RecommendResponse)
        : req.harvest === 'tomorrow'
          ? (require('./fixtures/recommend_price_crash.fixture.json') as RecommendResponse)
          : (require('./fixtures/recommend.fixture.json') as RecommendResponse);
    return { ...base, impact: { ...base.impact, redirected_kg: req.quantity_kg } };
  },
  // Rescue: trader split -> the trader-split fixture; no split -> the estimate fixture, except at an origin
  // far from the synthetic test region (no weather there), which answers 422 split_required.
  async rescue(req: RescueRequest): Promise<RescueResponse> {
    await delay(600);
    if (req.edible_kg != null) return require('./fixtures/rescue_trader.fixture.json') as RescueResponse;
    if (req.origin.lat > 20) throw new ApiError(422, 'split_required');
    return require('./fixtures/rescue.fixture.json') as RescueResponse;
  },
  // The stored ten-load plan from the backend tests, whatever loads are sent.
  async plan(_req: PlanRequest): Promise<PlanResponse> {
    await delay(500);
    return require('./fixtures/plan.fixture.json') as PlanResponse;
  },
  async speak(): Promise<SpeakResponse> {
    await delay(300);
    // No fixture audio: exercises the "audio hidden" state.
    throw new ApiError(503, 'speak_unavailable');
  },
  async impact(): Promise<ImpactResponse> {
    await delay(300);
    return require('./fixtures/impact.fixture.json') as ImpactResponse;
  },
};
