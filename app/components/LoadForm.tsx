// Typed load form, shared by New load and Confirm. Highlighted fields need checking.
import * as Location from 'expo-location';
import { useState } from 'react';
import { TextInput, View } from 'react-native';
import { CROPS, type Harvest } from '../api/types';
import { fmtNum } from '../i18n';
import { UNIT_KG } from '../lib/recommend';
import { useSession, type LoadDraft } from '../lib/session';
import { C, SIZE, fontFor } from '../lib/theme';
import { Btn, Chip, T, s } from './ui';

type Unit = keyof typeof UNIT_KG | 'box';
const HARVESTS: Harvest[] = ['today', 'tomorrow', 'harvested'];

const fmtCoords = (lat: number | null, lon: number | null) =>
  lat !== null && lon !== null ? `${lat.toFixed(4)}, ${lon.toFixed(4)}` : '';

/** "13.14, 78.13" (comma or space separated) -> coordinates, or null. */
function parseCoords(text: string): { lat: number; lon: number } | null {
  const parts = text.trim().split(/[\s,]+/);
  if (parts.length !== 2) return null;
  const [lat, lon] = parts.map(Number);
  return Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180
    ? { lat, lon }
    : null;
}

export function LoadForm({
  draft,
  onChange,
  highlight,
}: {
  draft: LoadDraft;
  onChange: (d: LoadDraft) => void;
  highlight?: (keyof LoadDraft)[];
}) {
  const { t, lang, crop: radarCrop, unitBoxKg } = useSession();
  const [unit, setUnit] = useState<Unit>('kg');
  const [qtyText, setQtyText] = useState(draft.quantity_kg ? String(draft.quantity_kg) : '');
  const [locMsg, setLocMsg] = useState<string | null>(null);
  const [coordText, setCoordText] = useState(fmtCoords(draft.lat, draft.lon));
  const boxKg = draft.crop && draft.crop === radarCrop ? unitBoxKg : null;
  const hl = (k: keyof LoadDraft) => !!highlight?.includes(k);

  function setQty(text: string, u: Unit) {
    setQtyText(text);
    setUnit(u);
    const n = Number(text.replace(/,/g, ''));
    const factor = u === 'box' ? boxKg : UNIT_KG[u];
    onChange({ ...draft, quantity_kg: text && n > 0 && factor ? n * factor : null });
  }

  async function useLocation() {
    setLocMsg(null);
    try {
      const perm = await Location.requestForegroundPermissionsAsync();
      if (!perm.granted) throw new Error('denied');
      const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      const geo = await Location.reverseGeocodeAsync(pos.coords).catch(() => []);
      const place = geo[0]?.city ?? geo[0]?.district ?? geo[0]?.subregion ?? draft.origin_place;
      onChange({ ...draft, lat: pos.coords.latitude, lon: pos.coords.longitude, origin_place: place ?? null });
      setCoordText(fmtCoords(pos.coords.latitude, pos.coords.longitude));
    } catch {
      // The API needs coordinates (422 origin_unknown): ask for location access or typed coordinates.
      setLocMsg(t('err_origin_unknown'));
    }
  }

  function setCoords(text: string) {
    setCoordText(text);
    const c = parseCoords(text);
    onChange({ ...draft, lat: c?.lat ?? null, lon: c?.lon ?? null });
  }

  const inputStyle = (k: keyof LoadDraft) => ({
    minHeight: SIZE.touch,
    borderWidth: hl(k) ? 3 : 2,
    borderColor: hl(k) ? C.highlightBorder : C.border,
    backgroundColor: hl(k) ? C.highlight : C.bg,
    borderRadius: 8,
    paddingHorizontal: 12,
    fontSize: SIZE.large,
    color: C.text,
    fontFamily: fontFor(lang),
  });

  return (
    <View style={{ gap: 10 }}>
      <T bold>{t('crop')}</T>
      <View style={s.row}>
        {CROPS.map((c) => (
          <Chip
            key={c}
            label={t(`crop_${c}`)}
            selected={draft.crop === c}
            highlight={hl('crop')}
            onPress={() => onChange({ ...draft, crop: c })}
          />
        ))}
      </View>

      <T bold>{t('quantity')}</T>
      <TextInput
        value={qtyText}
        onChangeText={(v) => setQty(v, unit)}
        keyboardType="numeric"
        accessibilityLabel={t('quantity')}
        style={inputStyle('quantity_kg')}
      />
      <View style={s.row}>
        {(['kg', 'box', 'quintal', 'tonne'] as Unit[]).map((u) => (
          <Chip
            key={u}
            label={t(`unit_${u}`)}
            selected={unit === u}
            onPress={() => setQty(qtyText, u)}
          />
        ))}
      </View>
      {unit === 'box' && !boxKg && <T color={C.errorBg}>{t('box_unavailable')}</T>}
      {unit !== 'kg' && draft.quantity_kg ? <T>{t('kg_value', { v: fmtNum(draft.quantity_kg) })}</T> : null}

      <T bold>{t('place')}</T>
      <TextInput
        value={draft.origin_place ?? ''}
        onChangeText={(v) => onChange({ ...draft, origin_place: v || null })}
        accessibilityLabel={t('place')}
        style={inputStyle('origin_place')}
      />
      <Btn kind="secondary" label={t('use_location')} onPress={() => void useLocation()} />
      {locMsg && <T color={C.errorBg}>{locMsg}</T>}
      <T bold>{t('coords')}</T>
      <TextInput
        value={coordText}
        onChangeText={setCoords}
        keyboardType="numbers-and-punctuation"
        placeholder="13.14, 78.13"
        accessibilityLabel={t('coords')}
        style={inputStyle('lat')}
      />
      {coordText.trim() !== '' && draft.lat === null && <T color={C.errorBg}>{t('coords_invalid')}</T>}

      <T bold>{t('harvest')}</T>
      <View style={s.row}>
        {HARVESTS.map((h) => (
          <Chip
            key={h}
            label={t(`harvest_${h}`)}
            selected={draft.harvest === h}
            highlight={hl('harvest')}
            onPress={() => onChange({ ...draft, harvest: h })}
          />
        ))}
      </View>
    </View>
  );
}
