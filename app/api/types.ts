// Request/response types for the AnnaSetu API (CLAUDE.md Section 13).
// Shapes match backend/handlers/advisor.py and voice.py and the stored responses in backend/tests/api_fixtures/.

export type Lang =
  | 'en'
  | 'hi'
  | 'bn'
  | 'mr'
  | 'te'
  | 'ta'
  | 'gu'
  | 'ur'
  | 'kn'
  | 'or'
  | 'ml'
  | 'pa'
  | 'as'
  | 'mai'
  | 'sat'
  | 'ks'
  | 'ne'
  | 'sd'
  | 'doi'
  | 'kok'
  | 'mni';
/** A crop with a routing profile (GET /crops routing: true); all 50 preloaded fruits and vegetables (D33). */
export type CropId = string;
export const DEFAULT_MY_CROPS: CropId[] = ['tomato', 'onion', 'potato']; // until the farmer picks theirs in Settings
/** Any AGMARKNET commodity id from GET /crops (config/commodities.json); the Glut Radar takes any (D24). */
export type RadarCropId = string;
export type RiskLevel = 'safe' | 'watch' | 'glut';
export type Mode = 'predictive' | 'same_day';
export type Harvest = 'today' | 'tomorrow' | 'harvested';
/** 'hold' = keep a storable crop (no outlet); 'compost' can also be a fallback with no outlet.
 * feed, biogas and compost are the Recover rung (CLAUDE.md D19). */
export type OutletType = 'mandi' | 'processor' | 'food_bank' | 'feed' | 'biogas' | 'compost' | 'hold';

export interface Range {
  low: number;
  mid: number;
  high: number;
}

export interface Freshness {
  as_of_date: string;
  stale: boolean;
  prices_date?: string | null; // oldest latest report of the recommended and nearest markets (D34)
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
  crop: RadarCropId;
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
  crop: RadarCropId;
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

/**
 * lat and lon, or a typed city, town or village (lat/lon null) that the API matches to a market or district name;
 * 422 origin_unknown when neither works.
 */
export interface Origin {
  lat: number | null;
  lon: number | null;
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
  /** null for hold and for the compost fallback with no seeded outlet in radius. */
  outlet_id: string | null;
  /** Absent for hold and for the compost fallback. */
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

/**
 * Impact Ledger (CLAUDE.md Section 9 Step 6). kept_out_of_landfill_kg = Prevented (waste_avoided_kg) + Rescued +
 * Recovered; redirected_kg is never added. waste_avoided_kg: null = not yet estimated; any value can be negative
 * (the trip loses more than it saves). biogas_energy: null while the biogas yield is unsourced.
 */
export interface Impact {
  kept_out_of_landfill_kg: Range | null;
  rescued_kg: number;
  recovered_kg: number;
  biogas_kg: number;
  biogas_energy: number | null;
  biogas_energy_unit: string | null;
  redirected_kg: number;
  waste_avoided_kg: Range | null;
  money_saved_rs?: Range | null; // Prevent loads: expected earnings vs the nearest mandi (net x share that sells)
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

// ---------- POST /recommend, source "mandi_unsold" (Rescue, Step 5b) ----------

/** edible_kg and spoiled_kg: both or neither; omitted = the engine proposes the split (needs weather). */
export interface RescueRequest {
  source: 'mandi_unsold';
  crop: CropId;
  quantity_kg: number;
  hours_since_harvest: number;
  edible_kg?: number;
  spoiled_kg?: number;
  origin: Origin;
  language: Lang;
  plan_id?: string;
}

export interface Split {
  edible_kg: number;
  spoiled_kg: number;
  source: 'estimate' | 'trader';
}

export interface RescueResponse extends Envelope, FixtureMark {
  plan_id: string;
  source: 'mandi_unsold';
  data: Freshness;
  crop: CropId;
  quantity_kg: number;
  split: Split;
  /** Processor or food bank for the edible part; null when none is in radius. */
  top: OutletOption | null;
  /** Feed, biogas or compost for the spoiled part (and the edible part when top is null); null when none. */
  recover: OutletOption | null;
  alternatives: OutletOption[];
  impact: Impact;
  explanation: Explanation;
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
  | 'split_required'
  | 'speak_language_unsupported'
  | 'transcribe_failed'
  | 'speak_failed'
  | 'internal_error'
  | (string & {});

export interface ApiErrorBody {
  error: ApiErrorCode;
  message?: string;
}

// ---------- GET /crops, POST /crops/fetch (D24) ----------

/** ready: data loaded for the radar; fetching: queued, check back later; available: not loaded yet. */
export type CropStatus = 'ready' | 'fetching' | 'available';

export interface CropInfo {
  crop_id: RadarCropId;
  name: string; // AGMARKNET commodity name (English)
  category: string | null;
  markets: number; // markets that reported it in the source data
  preload: boolean; // loaded daily (top fruits and vegetables)
  routing: boolean; // full crop profile: recommendations work
  names?: Partial<Record<Lang, string>>; // routable crops: names from the crop profile (en, hi, kn)
  status?: CropStatus; // only with ?crop=
}

export interface CropsResponse extends FixtureMark {
  crops: CropInfo[];
}

export interface FetchResponse extends FixtureMark {
  crop: RadarCropId;
  status: CropStatus;
}
