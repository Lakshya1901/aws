// Request/response types for the AnnaSetu API (CLAUDE.md Section 13).
// Fields marked "ASSUMED" are not spelled out in Section 13; the backend must match them.

export type Lang = 'en' | 'hi' | 'kn';
export type CropId = 'tomato' | 'onion' | 'potato' | 'banana';
export const CROPS: CropId[] = ['tomato', 'onion', 'potato', 'banana']; // MVP crops (Section 6)
export type RiskLevel = 'safe' | 'watch' | 'glut';
export type Mode = 'predictive' | 'same_day';
export type Harvest = 'today' | 'tomorrow' | 'harvested';
export type OutletType = 'mandi' | 'processor' | 'food_bank' | 'feed_compost';

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

// ---------- GET /risk?crop=&state=&lat=&lon= ----------

export interface RiskQuery {
  crop: CropId;
  state?: string;
  lat?: number;
  lon?: number;
}

export interface RiskMarket {
  market_id: string;
  name: string; // ASSUMED: display name
  state: string;
  risk_level: RiskLevel | null; // null = market not reported recently (ASSUMED)
  arrival_ratio: number | null;
  modal_price_rs_per_kg: number | null; // ASSUMED name for "price"
  price_change_3d: number | null; // fraction, e.g. -0.18 (ASSUMED name for "change_3d")
  as_of_date: string | null;
  stale: boolean; // ASSUMED per-market flag (Section 8.6)
  lead_days: number | null; // only meaningful in predictive mode
  distance_km: number | null; // ASSUMED: from the requested lat/lon
  distance_approx: boolean; // ASSUMED: true when haversine fallback used
}

export interface RiskResponse extends FixtureMark {
  crop: CropId;
  mode: Mode;
  replay_date: string | null; // ASSUMED: set when replaying historical data
  unit_box_kg: number | null; // ASSUMED: crop profile box size, for the box unit
  markets: RiskMarket[];
}

// ---------- POST /voice/upload ----------

export interface VoiceUploadRequest {
  language: Lang;
  content_type: string;
}

export interface VoiceUploadResponse extends FixtureMark {
  upload_url: string; // ASSUMED name for "presigned S3 URL"
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

export interface Origin {
  lat: number | null; // ASSUMED nullable when only a place name is known
  lon: number | null;
  place: string;
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
  outlet_id: string;
  name: string; // ASSUMED: display name
  type: OutletType;
  net_rs_per_kg: Range;
  distance_km?: number | null;
  distance_approx?: boolean; // ASSUMED: haversine fallback -> "approx."
  drive_hours?: number | null;
  spoilage_share?: number | null;
  risk_level?: RiskLevel | null;
  arrival_ratio?: number | null;
  partnered?: boolean; // ASSUMED: false -> "Not yet partnered" label
}

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

export interface RecommendResponse extends FixtureMark {
  plan_id: string;
  mode: Mode;
  replay_date: string | null; // ASSUMED
  demo_loads: boolean; // ASSUMED: true -> "Demo loads" label
  data: Freshness;
  top: OutletOption;
  default: OutletOption;
  alternatives: OutletOption[];
  impact: Impact;
  explanation: Explanation;
  advice: Advice | null; // ASSUMED shape for Section 13 "advice"
  harvest_cost_rs_per_kg: number | null; // ASSUMED: for the advice warning
  assumptions_used: string[];
}

// ---------- POST /plan ----------

export interface PlanLoad {
  load_id: string; // ASSUMED: client-generated id
  crop: CropId;
  quantity_kg: number;
  origin: Origin;
  harvest: Harvest;
  chosen_outlet_id?: string; // ASSUMED: records "Use this" or an override
  override?: boolean; // ASSUMED: true when chosen != recommended
}

export interface PlanRequest {
  loads: PlanLoad[];
  language: Lang;
  plan_id?: string; // ASSUMED
}

export interface PlanAllocation {
  load_id: string;
  outlet: OutletOption;
  quantity_kg: number;
  advice: Advice | null;
}

export interface MarketAddition {
  market_id: string;
  name: string;
  added_kg: number; // dA
  capped: boolean; // ASSUMED: allocation stopped here to avoid pushing it into glut
}

export interface PlanResponse extends FixtureMark {
  plan_id: string;
  mode: Mode;
  replay_date: string | null;
  demo_loads: boolean;
  data: Freshness;
  allocations: PlanAllocation[];
  markets: MarketAddition[]; // ASSUMED name for "dA per market"
  impact: Impact; // total
}

// ---------- POST /speak ----------

export interface SpeakRequest {
  text: string;
  language: 'hi' | 'en';
}

export interface SpeakResponse extends FixtureMark {
  audio_url: string; // ASSUMED name for "presigned MP3 URL"
}

// ---------- GET /impact?plan_id= ----------

export interface ImpactResponse extends Impact, FixtureMark {
  plan_id: string;
}

// ---------- Errors ----------

/** ASSUMED error body: {"error": "<code>", "message": "..."}. */
export type ApiErrorCode = 'no_markets_in_radius' | 'crop_not_configured' | string;

export interface ApiErrorBody {
  error: ApiErrorCode;
  message?: string;
}
