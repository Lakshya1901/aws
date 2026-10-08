import { router } from 'expo-router';
import { api } from '../api/client';
import type { RecommendRequest } from '../api/types';
import { originOf, useSession, type LoadDraft } from './session';

export const UNIT_KG = { kg: 1, quintal: 100, tonne: 1000 } as const;

export function draftComplete(d: LoadDraft): boolean {
  return !!d.crop && !!d.quantity_kg && d.quantity_kg > 0 && !!d.harvest && !!(d.origin_place || d.lat !== null);
}

/** POST /recommend for a complete draft, store it, open the Recommendation screen. Throws on failure. */
export function useRecommend() {
  const { lang, planId, setPlanId, setCurrent } = useSession();
  return async (d: LoadDraft) => {
    if (!d.crop || !d.quantity_kg || !d.harvest) throw new Error('incomplete');
    const req: RecommendRequest = {
      crop: d.crop,
      quantity_kg: d.quantity_kg,
      origin: originOf(d),
      harvest: d.harvest,
      language: lang ?? 'en',
      ...(planId ? { plan_id: planId } : {}),
    };
    const res = await api.recommend(req);
    if (!planId) setPlanId(res.plan_id);
    setCurrent({ req, res });
    router.push('/recommendation');
  };
}
