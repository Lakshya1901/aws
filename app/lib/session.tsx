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
import { isRouterCrop } from '../api/types';
import { translate, type CopyKey } from '../i18n';

const LANG_KEY = 'annasetu.lang';
const riskKey = (crop: RadarCropId) => `annasetu.risk.${crop}`;

export interface LoadDraft {
  crop: CropId | null;
  quantity_kg: number | null;
  origin_place: string | null;
  harvest: Harvest | null;
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
  cropLabel: (c: RadarCropId) => string; // translated name for the MVP crops, else the AGMARKNET name
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
  lat: null,
  lon: null,
};

const Ctx = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [lang, setLangState] = useState<Lang | null>(null);
  const [crop, setCrop] = useState<RadarCropId>('tomato');
  const [crops, setCrops] = useState<CropInfo[]>([]);
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
        if (v === 'en' || v === 'hi' || v === 'kn') setLangState(v);
      })
      .catch(() => {})
      .finally(() => setReady(true));
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
    (c: RadarCropId) =>
      isRouterCrop(c) ? t(`crop_${c}`) : (crops.find((x) => x.crop_id === c)?.name ?? c),
    [t, crops],
  );

  const addLoad = useCallback((l: PlanLoad) => {
    setLoads((prev) => [...prev.filter((p) => p.load_id !== l.load_id), l]);
  }, []);

  const value = useMemo<Session>(
    () => ({
      ready, lang, setLang, t, crop, setCrop, crops, setCrops, cropLabel, unitBoxKg, setUnitBoxKg, coords, setCoords,
      draft, setDraft, voice, setVoice, current, setCurrent, loads, addLoad, planId, setPlanId,
    }),
    [ready, lang, setLang, t, crop, crops, cropLabel, unitBoxKg, coords, draft, voice, current, loads, addLoad, planId],
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
