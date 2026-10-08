// Request/response types for the AnnaSetu API (CLAUDE.md Section 13).
// Shapes match backend/handlers/advisor.py and voice.py and the stored responses in backend/tests/api_fixtures/.

export type Lang = 'en' | 'hi' | 'kn';
export type CropId = 'tomato' | 'onion' | 'potato' | 'banana';
export const CROPS: CropId[] = ['tomato', 'onion', 'potato', 'banana']; // MVP crops (Section 6)
export type RiskLevel = 'safe' | 'watch' | 'glut';
export type Mode = 'predictive' | 'same_day';
export type Harvest = 'today' | 'tomorrow' | 'harvested';
/** 'hold' = keep a storable crop (no outlet); 'feed_compost' can also be a fallback with no outlet. */
export type OutletType = 'mandi' | 'processor' | 'food_bank' | 'feed_compost' | 'hold';

export interface Range {
  low: number;
  mid: number;
  high: number;
}

export interface Freshness {
  as_of_date: string;
  stale: boolean;
}

/** Present on every fixture so fixture numbers can never pass as real data. */
export interface FixtureMark {
  _fixture?: true;
}

/** Set on every advisor response: replay_date when replaying historical data; demo_loads then true. */
interface Envelope {
  replay_date: string | null;
  demo_loads: boolean;
}

// ---------- GET /risk?crop=&state=&lat=&lon= ----------

export interface RiskQuery {
  crop: CropId;
  state?: string;
  lat?: number;
  lon?: number;
}

export interface RiskMarket {
  market_id: string;
  name: string;
  state: string;
  risk_level: RiskLevel | null; // null = market not reported recently
  arrival_ratio: number | null;
  modal_price_rs_per_kg: number | null;
  price_change_3d: number | null; // fraction, e.g. -0.18
  as_of_date: string | null;
  stale: boolean;
  data_complete: boolean | null;
  lead_days: number | null; // only meaningful in predictive mode
  distance_km: number | null; // from the requested lat/lon; null without one
  distance_approx: boolean; // true when the haversine fallback was used
}

export interface RiskResponse extends Envelope, FixtureMark {
  crop: CropId;
  mode: Mode;
  unit_box_kg: number | null;
  data: Freshness;
  markets: RiskMarket[];
}

// ---------- POST /voice/upload ----------

export interface VoiceUploadRequest {
  language: Lang;
  content_type: string;
}

export interface VoiceUploadResponse extends FixtureMark {
  upload_url: string;
  audio_key: string;
}

// ---------- POST /voice/parse ----------

export interface VoiceParseRequest {
  audio_key: string;
  language: Lang;
}

export interface ParsedFields {
  crop: CropId | null;
  quantity_kg: number | null;
  origin_place: string | null;
  harvest: Harvest | null;
}

export interface VoiceParseResponse extends FixtureMark {
  transcript: string;
  fields: ParsedFields;
  confidence: 'high' | 'low';
}

// ---------- POST /recommend ----------

/** lat and lon are required: the API answers 422 origin_unknown without them (place names are not geocoded). */
export interface Origin {
  lat: number;
  lon: number;
  place?: string | null;
}

export interface RecommendRequest {
  crop: CropId;
  quantity_kg: number;
  origin: Origin;
  harvest: Harvest;
  language: Lang;
  plan_id?: string;
}

export interface OutletOption {
  /** null for hold and for the feed/compost fallback with no seeded outlet in radius. */
  outlet_id: string | null;
  /** Absent for hold and for the feed/compost fallback. */
  name?: string;
  type: OutletType;
  state?: string;
  /** null = not yet estimated (processor without an offer, hold, fallback compost). Can be negative. */
  net_rs_per_kg: Range | null;
  net_note?: string | null;
  price_rs_per_kg?: Range;
  distance_km?: number | null;
  distance_approx?: boolean; // haversine fallback -> "approx."
  drive_hours?: number | null;
  spoilage_share?: number | null;
  spoilage_range?: Range;
  risk_level?: RiskLevel | null; // mandis only
  arrival_ratio?: number | null; // mandis only
  projected_arrival_ratio?: number | null;
  projected_risk_level?: RiskLevel | null;
  price_change_3d?: number | null;
  stale?: boolean;
  latest_date?: string | null;
  data_complete?: boolean | null;
  contact?: string;
  note?: string;
  /** Second Life outlets only (false -> "Not yet partnered"). Absent on mandis: not applicable. */
  partnered?: boolean;
}

/** waste_avoided_kg: null = not yet estimated; any value can be negative (the trip loses more than it saves). */
export interface Impact {
  redirected_kg: number;
  waste_avoided_kg: Range | null;
  extra_km: number | null;
  diesel_l: number | null;
  co2_kg: number | null;
  water_l: number | null;
}

export interface Explanation {
  language: Lang;
  text: string;
  source: 'bedrock' | 'template';
}

export type Advice = 'delay_harvest' | 'harvest_to_order';

export interface RecommendResponse extends Envelope, FixtureMark {
  plan_id: string;
  mode: Mode;
  data: Freshness;
  crop: CropId;
  quantity_kg: number;
  top: OutletOption;
  default: OutletOption;
  /** May include the default market again; ordered fresh markets by net value, then Second Life. */
  alternatives: OutletOption[];
  impact: Impact;
  explanation: Explanation;
  advice: Advice | null;
  harvest_cost_rs_per_kg: number;
  assumptions_used: string[];
}

// ---------- POST /plan ----------

export interface PlanLoad {
  load_id: string; // client-generated id
  crop: CropId;
  quantity_kg: number;
  origin: Origin;
  harvest: Harvest;
  chosen_outlet_id?: string | null; // records "Use this" or an override
  override?: boolean; // true when chosen != recommended
}

export interface PlanRequest {
  loads: PlanLoad[];
  language: Lang;
  plan_id?: string;
}

export interface PlanAllocation {
  load_id: string;
  crop: CropId;
  quantity_kg: number;
  outlet: OutletOption;
  default: OutletOption;
  advice: Advice | null;
  impact: Impact;
}

export interface MarketAddition {
  market_id: string;
  name: string | null;
  crop: CropId | null; // null for a market capped without any load added
  added_kg: number; // dA
  capped: boolean; // passed over so this plan's loads do not push it into glut
}

export interface PlanResponse extends Envelope, FixtureMark {
  plan_id: string;
  mode: Mode;
  modes: Partial<Record<CropId, Mode>>;
  data: Freshness;
  allocations: PlanAllocation[];
  markets: MarketAddition[];
  impact: Impact; // total
  assumptions_used: string[];
}

// ---------- POST /speak ----------

export interface SpeakRequest {
  text: string;
  language: 'hi' | 'en';
}

export interface SpeakResponse extends FixtureMark {
  audio_url: string;
}

// ---------- GET /impact?plan_id= ----------

export interface ImpactResponse extends Impact, FixtureMark {
  plan_id: string;
}

// ---------- Errors ----------

/** Error body {"error": "<code>", "message": "..."}; 400 bad_request, 404 plan_not_found, 422 for the rest, 502 voice. */
export type ApiErrorCode =
  | 'bad_request'
  | 'plan_not_found'
  | 'not_found'
  | 'origin_unknown'
  | 'no_markets_in_radius'
  | 'crop_not_configured'
  | 'drive_time_unavailable'
  | 'temperature_unavailable'
  | 'speak_language_unsupported'
  | 'transcribe_failed'
  | 'speak_failed'
  | 'internal_error'
  | (string & {});

export interface ApiErrorBody {
  error: ApiErrorCode;
  message?: string;
}
