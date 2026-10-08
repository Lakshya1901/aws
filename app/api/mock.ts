// Mock mode (EXPO_PUBLIC_API_MOCK=1): returns development fixtures. Never used in real mode.
// Every fixture carries "_fixture": true and the UI shows a FIXTURE banner for it.
import { ApiError } from './errors';
import type {
  ImpactResponse,
  PlanRequest,
  PlanResponse,
  RecommendRequest,
  RecommendResponse,
  RiskQuery,
  RiskResponse,
  SpeakResponse,
  VoiceParseResponse,
  VoiceUploadResponse,
} from './types';

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export const mock = {
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
  // tomato: glut-day recommendation; onion: Second Life states;
  // potato: 422 no markets; banana: 422 crop not set up.
  async recommend(req: RecommendRequest): Promise<RecommendResponse> {
    await delay(600);
    if (req.crop === 'potato') throw new ApiError(422, 'no_markets_in_radius');
    if (req.crop === 'banana') throw new ApiError(422, 'crop_not_configured');
    const base =
      req.crop === 'tomato'
        ? (require('./fixtures/recommend.fixture.json') as RecommendResponse)
        : (require('./fixtures/recommend_second_life.fixture.json') as RecommendResponse);
    return { ...base, impact: { ...base.impact, redirected_kg: req.quantity_kg } };
  },
  async plan(req: PlanRequest): Promise<PlanResponse> {
    await delay(500);
    const base = require('./fixtures/plan.fixture.json') as PlanResponse;
    const rec = require('./fixtures/recommend.fixture.json') as RecommendResponse;
    const outlets = [rec.top, rec.default, ...rec.alternatives];
    return {
      ...base,
      allocations: req.loads.map((l) => ({
        load_id: l.load_id,
        outlet: outlets.find((o) => o.outlet_id === l.chosen_outlet_id) ?? rec.top,
        quantity_kg: l.quantity_kg,
        advice: null,
      })),
    };
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
