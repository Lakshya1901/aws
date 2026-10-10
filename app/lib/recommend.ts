import * as Location from 'expo-location';
import { router } from 'expo-router';
import model from '../../config/model.json';
import { ApiError, api } from '../api/client';
import type { OutletOption, RecommendRequest } from '../api/types';
import { useSession, type LoadDraft } from './session';

export const UNIT_KG = { kg: 1, quintal: 100, tonne: 1000 } as const;

export function draftComplete(d: LoadDraft): boolean {
  return (
    !!d.crop && !!d.quantity_kg && d.quantity_kg > 0 && !!d.harvest && !!(d.origin_place || d.lat !== null) &&
    (d.harvest !== 'harvested' || d.days_since_harvest !== null)
  );
}

/**
 * D10: cite an arrival multiple only when it drives the market's watch/glut level
 * (risk watch or glut and arrival_ratio >= the model's watch_ratio). Same rule as the backend explanation.
 */
export function ratioDriven(o: OutletOption): boolean {
  return (
    (o.risk_level === 'watch' || o.risk_level === 'glut') &&
    o.arrival_ratio != null &&
    o.arrival_ratio >= model.risk.watch_ratio
  );
}

/** Device location via expo-location; null when permission is denied or no fix is available. */
export async function deviceCoords(): Promise<{ lat: number; lon: number } | null> {
  try {
    const perm = await Location.requestForegroundPermissionsAsync();
    if (!perm.granted) return null;
    const pos =
      (await Location.getLastKnownPositionAsync()) ??
      (await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }));
    return pos ? { lat: pos.coords.latitude, lon: pos.coords.longitude } : null;
  } catch {
    return null;
  }
}

/**
 * POST /recommend for a complete draft, store it, open the Recommendation screen. Throws on failure.
 * Origin: the draft's coordinates, else the typed place (resolved by the API), else the device location;
 * without any, throw origin_unknown so the screen asks for location access or a place.
 */
export function useRecommend() {
  const { lang, planId, setPlanId, setCurrent, coords, setCoords } = useSession();
  return async (d: LoadDraft) => {
    if (!d.crop || !d.quantity_kg || !d.harvest) throw new Error('incomplete');
    // Coordinates from "Use my location" win; else the typed city, town or village; else the device location.
    const typed = d.origin_place?.trim() ? { lat: null, lon: null } : null;
    let at = d.lat !== null && d.lon !== null ? { lat: d.lat, lon: d.lon } : (typed ?? coords);
    if (!at) {
      at = await deviceCoords();
      if (at) setCoords(at);
    }
    if (!at) throw new ApiError(422, 'origin_unknown');
    const req: RecommendRequest = {
      crop: d.crop,
      quantity_kg: d.quantity_kg,
      origin: { lat: at.lat, lon: at.lon, place: d.origin_place },
      harvest: d.harvest,
      ...(d.harvest === 'harvested' && d.days_since_harvest !== null ? { days_since_harvest: d.days_since_harvest } : {}),
      language: lang ?? 'en',
      ...(planId ? { plan_id: planId } : {}),
    };
    const res = await api.recommend(req);
    if (!planId) setPlanId(res.plan_id);
    setCurrent({ req, res });
    router.push('/recommendation');
  };
}
