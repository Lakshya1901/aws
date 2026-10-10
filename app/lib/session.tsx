// Session state shared across screens, plus AsyncStorage persistence for language and last risk data.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type {
  CropId,
  CropInfo,
  Harvest,
  Lang,
  ParsedFields,
  PlanLoad,
  RadarCropId,
  RecommendRequest,
  RecommendResponse,
  RiskResponse,
} from '../api/types';
import { api, getDataMode, setDataMode as setClientDataMode, type DataMode } from '../api/client';
import { DEFAULT_MY_CROPS } from '../api/types';
import { LANG_INFO, translate, type CopyKey } from '../i18n';

const LANG_KEY = 'annasetu.lang';
const MY_CROPS_KEY = 'annasetu.mycrops.v1';
const DATA_KEY = 'annasetu.data.v1';
const ROUTING_FALLBACK = ['tomato', 'onion']; // before the crop catalogue loads
const riskKey = (crop: RadarCropId) => `annasetu.risk.${getDataMode()}.${crop}`;

export interface LoadDraft {
  crop: CropId | null;
  quantity_kg: number | null;
  origin_place: string | null;
  harvest: Harvest | null;
  days_since_harvest: number | null; // harvest "harvested": days ago (0 = today)
  lat: number | null;
  lon: number | null;
}

export interface VoiceResult {
  transcript: string;
  fields: ParsedFields;
  confidence: 'high' | 'low';
}

interface Session {
  ready: boolean;
  lang: Lang | null;
  setLang: (l: Lang) => void;
  t: (key: CopyKey, vars?: Record<string, string | number>) => string;
  crop: RadarCropId; // the Glut Radar crop: any commodity (D24)
  setCrop: (c: RadarCropId) => void;
  crops: CropInfo[]; // GET /crops catalogue, [] until loaded
  setCrops: (c: CropInfo[]) => void;
  cropLabel: (c: RadarCropId) => string; // translated name, else the profile's English name, else the AGMARKNET name
  canRoute: (c: RadarCropId | null) => boolean; // a routing profile exists (GET /crops)
  myCrops: CropId[]; // crops this farmer sells (Settings); shown first in every crop list
  setMyCrops: (c: CropId[]) => void;
  dataMode: DataMode; // live prices for today (default) or the saved demo glut day (Settings, D34)
  setDataMode: (m: DataMode) => void;
  unitBoxKg: number | null;
  setUnitBoxKg: (n: number | null) => void;
  coords: { lat: number; lon: number } | null;
  setCoords: (c: { lat: number; lon: number } | null) => void;
  draft: LoadDraft;
  setDraft: (d: LoadDraft) => void;
  voice: VoiceResult | null;
  setVoice: (v: VoiceResult | null) => void;
  current: { req: RecommendRequest; res: RecommendResponse } | null;
  setCurrent: (c: { req: RecommendRequest; res: RecommendResponse } | null) => void;
  loads: PlanLoad[];
  addLoad: (l: PlanLoad) => void;
  planId: string | null;
  setPlanId: (id: string | null) => void;
}

export const EMPTY_DRAFT: LoadDraft = {
  crop: null,
  quantity_kg: null,
  origin_place: null,
  harvest: null,
  days_since_harvest: null,
  lat: null,
  lon: null,
};

const Ctx = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [lang, setLangState] = useState<Lang | null>(null);
  const [crop, setCrop] = useState<RadarCropId>('tomato');
  const [crops, setCrops] = useState<CropInfo[]>([]);
  const [myCrops, setMyCropsState] = useState<CropId[]>(DEFAULT_MY_CROPS);
  const [dataMode, setDataModeState] = useState<DataMode>(getDataMode());
  const [unitBoxKg, setUnitBoxKg] = useState<number | null>(null);
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [draft, setDraft] = useState<LoadDraft>(EMPTY_DRAFT);
  const [voice, setVoice] = useState<VoiceResult | null>(null);
  const [current, setCurrent] = useState<Session['current']>(null);
  const [loads, setLoads] = useState<PlanLoad[]>([]);
  const [planId, setPlanId] = useState<string | null>(null);

  useEffect(() => {
    AsyncStorage.getItem(LANG_KEY)
      .then((v) => {
        if (v && v in LANG_INFO) setLangState(v as Lang);
      })
      .catch(() => {})
      .finally(() => setReady(true));
    AsyncStorage.getItem(MY_CROPS_KEY)
      .then((v) => {
        const list = v ? (JSON.parse(v) as CropId[]) : null;
        if (Array.isArray(list) && list.length) setMyCropsState(list);
      })
      .catch(() => {});
    AsyncStorage.getItem(DATA_KEY)
      .then((v) => {
        if (v === 'live' || v === 'demo') {
          setClientDataMode(v);
          setDataModeState(v);
        }
      })
      .catch(() => {});
    api.crops().then((r) => setCrops(r.crops), () => {});
  }, []);

  // A plan never mixes live and demo data: switching starts a new one.
  const setDataMode = useCallback((m: DataMode) => {
    setClientDataMode(m);
    setDataModeState(m);
    setLoads([]);
    setPlanId(null);
    setCurrent(null);
    AsyncStorage.setItem(DATA_KEY, m).catch(() => {});
  }, []);

  const setMyCrops = useCallback((list: CropId[]) => {
    setMyCropsState(list);
    AsyncStorage.setItem(MY_CROPS_KEY, JSON.stringify(list)).catch(() => {});
  }, []);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    AsyncStorage.setItem(LANG_KEY, l).catch(() => {});
  }, []);

  const t = useCallback(
    (key: CopyKey, vars?: Record<string, string | number>) => translate(lang ?? 'en', key, vars),
    [lang],
  );

  const cropLabel = useCallback(
    (c: RadarCropId) => {
      const info = crops.find((x) => x.crop_id === c);
      const own = info?.names?.[lang ?? 'en'];
      if (own && lang !== 'en') return own;
      const key = `crop_${c}` as CopyKey;
      const copy = t(key);
      return copy !== key ? copy : (info?.names?.en ?? info?.name ?? c);
    },
    [t, crops, lang],
  );

  const canRoute = useCallback(
    (c: RadarCropId | null) =>
      c !== null && (crops.length ? !!crops.find((x) => x.crop_id === c)?.routing : ROUTING_FALLBACK.includes(c)),
    [crops],
  );

  const addLoad = useCallback((l: PlanLoad) => {
    setLoads((prev) => [...prev.filter((p) => p.load_id !== l.load_id), l]);
  }, []);

  const value = useMemo<Session>(
    () => ({
      ready, lang, setLang, t, crop, setCrop, crops, setCrops, cropLabel, canRoute, myCrops, setMyCrops, dataMode, setDataMode, unitBoxKg, setUnitBoxKg, coords, setCoords,
      draft, setDraft, voice, setVoice, current, setCurrent, loads, addLoad, planId, setPlanId,
    }),
    [ready, lang, setLang, t, crop, crops, cropLabel, canRoute, myCrops, setMyCrops, dataMode, setDataMode, unitBoxKg, coords, draft, voice, current, loads, addLoad, planId],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession(): Session {
  const s = useContext(Ctx);
  if (!s) throw new Error('useSession outside SessionProvider');
  return s;
}

export async function cacheRisk(crop: RadarCropId, data: RiskResponse): Promise<void> {
  try {
    await AsyncStorage.setItem(riskKey(crop), JSON.stringify(data));
  } catch {}
}

export async function readCachedRisk(crop: RadarCropId): Promise<RiskResponse | null> {
  try {
    const raw = await AsyncStorage.getItem(riskKey(crop));
    return raw ? (JSON.parse(raw) as RiskResponse) : null;
  } catch {
    return null;
  }
}
