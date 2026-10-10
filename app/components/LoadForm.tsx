// Typed load form, shared by New load and Confirm. Highlighted fields need checking.
import * as Location from 'expo-location';
import { useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';
import { router } from 'expo-router';
import type { Harvest } from '../api/types';
import { fmtNum } from '../i18n';
import { UNIT_KG } from '../lib/recommend';
import { useSession, type LoadDraft } from '../lib/session';
import { C, RADIUS, SIZE, fontFor } from '../lib/theme';
import { HarvestAge } from './HarvestAge';
import { Icon } from './Icon';
import { Btn, Chip, T, s } from './ui';

type Unit = keyof typeof UNIT_KG | 'box';
const HARVESTS: Harvest[] = ['today', 'tomorrow', 'harvested'];

/** The farmer's crops (Settings) that can be routed, plus the current choice if it is not among them. */
export function cropChoices(myCrops: string[], current: string | null, canRoute: (c: string) => boolean): string[] {
  const list = myCrops.filter(canRoute);
  return current && !list.includes(current) ? [...list, current] : list;
}

/** Place name for device coordinates (reverse geocode on the phone), or null. */
export async function placeName(lat: number, lon: number): Promise<string | null> {
  const geo = await Location.reverseGeocodeAsync({ latitude: lat, longitude: lon }).catch(() => []);
  const g = geo[0];
  return g?.city ?? g?.district ?? g?.subregion ?? g?.region ?? null;
}

/** Material segmented buttons: one outlined row, selected segment tonal with a check. */
function Segmented<V extends string>({
  options,
  value,
  onSelect,
  highlight,
}: {
  options: { value: V; label: string }[];
  value: V | null;
  onSelect: (v: V) => void;
  highlight?: boolean;
}) {
  return (
    <View
      style={{
        flexDirection: 'row',
        borderWidth: highlight ? 2 : 1,
        borderColor: highlight ? C.warnText : C.outline,
        backgroundColor: highlight ? C.warnBg : 'transparent',
        borderRadius: RADIUS.pill,
        overflow: 'hidden',
      }}
    >
      {options.map((o, i) => {
        const sel = o.value === value;
        return (
          <Pressable
            key={o.value}
            accessibilityRole="button"
            accessibilityState={{ selected: sel }}
            onPress={() => onSelect(o.value)}
            style={{
              flex: 1,
              minHeight: SIZE.touch,
              paddingHorizontal: 4,
              paddingVertical: 6,
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 4,
              backgroundColor: sel ? C.tonal : 'transparent',
              borderLeftWidth: i === 0 ? 0 : 1,
              borderLeftColor: highlight ? C.warnText : C.outline,
            }}
          >
            {sel ? <Icon name="check" size={16} color={C.onTonal} strokeWidth={2.6} /> : null}
            <T bold={sel} size={SIZE.small} color={sel ? C.onTonal : C.text} style={{ textAlign: 'center', flexShrink: 1 }}>
              {o.label}
            </T>
          </Pressable>
        );
      })}
    </View>
  );
}

export function LoadForm({
  draft,
  onChange,
  highlight,
  showNotHeard,
}: {
  draft: LoadDraft;
  onChange: (d: LoadDraft) => void;
  highlight?: (keyof LoadDraft)[];
  /** Confirm screen: empty fields say "Not heard" inside the field. */
  showNotHeard?: boolean;
}) {
  const { t, lang, crop: radarCrop, unitBoxKg, myCrops, canRoute, cropLabel } = useSession();
  const [unit, setUnit] = useState<Unit>('kg');
  const [qtyText, setQtyText] = useState(draft.quantity_kg ? String(draft.quantity_kg) : '');
  const [locMsg, setLocMsg] = useState<string | null>(null);
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
      // The place box shows where the phone is; the coordinates go to the API with it.
      const place = await placeName(pos.coords.latitude, pos.coords.longitude);
      onChange({ ...draft, lat: pos.coords.latitude, lon: pos.coords.longitude, origin_place: place ?? t('my_location') });
    } catch {
      setLocMsg(t('err_origin_unknown'));
    }
  }

  const inputStyle = (k: keyof LoadDraft) => ({
    minHeight: 56,
    borderWidth: hl(k) ? 2 : 1,
    borderColor: hl(k) ? C.warnText : C.outline,
    backgroundColor: hl(k) ? C.warnBg : C.bg,
    borderRadius: RADIUS.field,
    paddingHorizontal: 16,
    fontSize: SIZE.large,
    color: C.text,
    fontFamily: fontFor(lang),
  });
  const hint = showNotHeard ? t('not_heard') : undefined;
  const hintColor = C.muted;
  const label = (key: 'crop' | 'quantity' | 'place' | 'harvest', empty?: boolean) => (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      <T bold>{t(key)}</T>
      {showNotHeard && empty ? <T size={SIZE.label} color={hintColor}>{hint}</T> : null}
    </View>
  );

  return (
    <View style={{ gap: 20 }}>
      <View style={{ gap: 8 }}>
        {label('crop', draft.crop === null)}
        <View style={s.row}>
          {cropChoices(myCrops, draft.crop, canRoute).map((c) => (
            <Chip
              key={c}
              label={cropLabel(c)}
              selected={draft.crop === c}
              highlight={hl('crop')}
              onPress={() => onChange({ ...draft, crop: c })}
            />
          ))}
          <Chip label={t('more_crops')} selected={false} onPress={() => router.push('/settings')} />
        </View>
      </View>

      <View style={{ gap: 8 }}>
        {label('quantity')}
        <TextInput
          value={qtyText}
          onChangeText={(v) => setQty(v, unit)}
          keyboardType="numeric"
          placeholder={showNotHeard && !qtyText ? hint : undefined}
          placeholderTextColor={C.muted}
          accessibilityLabel={t('quantity')}
          style={inputStyle('quantity_kg')}
        />
        <Segmented
          options={(['kg', 'box', 'quintal', 'tonne'] as Unit[]).map((u) => ({ value: u, label: t(`unit_${u}`) }))}
          value={unit}
          onSelect={(u) => setQty(qtyText, u)}
        />
        {unit === 'box' && !boxKg && <T color={C.errorBg}>{t('box_unavailable')}</T>}
        {unit !== 'kg' && draft.quantity_kg ? <T color={C.muted}>{t('kg_value', { v: fmtNum(draft.quantity_kg) })}</T> : null}
      </View>

      <View style={{ gap: 8 }}>
        {label('place')}
        <TextInput
          value={draft.origin_place ?? ''}
          onChangeText={(v) => {
            onChange({ ...draft, origin_place: v || null, lat: null, lon: null }); // a typed place replaces GPS
          }}
          placeholder={showNotHeard && !draft.origin_place ? hint : undefined}
          placeholderTextColor={C.muted}
          accessibilityLabel={t('place')}
          style={inputStyle('origin_place')}
        />
        <Btn kind="text" icon="pin" label={t('use_location')} onPress={() => void useLocation()} style={{ alignSelf: 'flex-start' }} />
        {locMsg && <T color={C.errorBg}>{locMsg}</T>}
      </View>

      <View style={{ gap: 8 }}>
        {label('harvest', draft.harvest === null)}
        <Segmented
          options={HARVESTS.map((h) => ({ value: h, label: t(`harvest_${h}`) }))}
          value={draft.harvest}
          onSelect={(h) => onChange({ ...draft, harvest: h })}
          highlight={hl('harvest')}
        />
        {draft.harvest === 'harvested' && (
          <>
            <T size={SIZE.small} color={C.muted}>
              {t('harvested_when')}
            </T>
            <HarvestAge days={draft.days_since_harvest} onSelect={(d) => onChange({ ...draft, days_since_harvest: d })} />
          </>
        )}
      </View>
    </View>
  );
}
