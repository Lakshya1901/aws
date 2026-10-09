// Unsold stock (Rescue, CLAUDE.md Section 9 Step 5b): a trader at a city mandi logs end-of-day stock.
// Edible part -> processor or food bank; spoiled part -> feed, biogas or compost. Same POST /recommend.
// The edible/spoiled split is optional: empty = the engine proposes it (needs weather at the place);
// without weather (Delhi, Mumbai) the API answers 422 split_required and the trader enters both.
import { useState } from 'react';
import { TextInput, View } from 'react-native';
import { ApiError, api } from '../api/client';
import { CROPS, isRouterCrop, type CropId, type OutletOption, type RescueResponse } from '../api/types';
import { ImpactRows } from '../components/ImpactRows';
import { parseCoords } from '../components/LoadForm';
import { useOutletLabels } from '../components/RecommendationCard';
import { Banner, Btn, Chip, DataBanners, Loading, Screen, T, s, useErrorText } from '../components/ui';
import { fmtNum } from '../i18n';
import { deviceCoords } from '../lib/recommend';
import { useSession } from '../lib/session';
import { C, SIZE, fontFor } from '../lib/theme';

const num = (text: string): number | null => {
  const n = Number(text.replace(/,/g, ''));
  return text.trim() !== '' && Number.isFinite(n) && n >= 0 ? n : null;
};

export default function RescueScreen() {
  const { t, lang, crop: radarCrop, coords, setCoords, planId, setPlanId } = useSession();
  const L = useOutletLabels();
  const errorText = useErrorText();
  const [crop, setCrop] = useState<CropId>(isRouterCrop(radarCrop) ? radarCrop : 'tomato');
  const [qty, setQty] = useState('');
  const [hours, setHours] = useState('');
  const [edible, setEdible] = useState('');
  const [spoiled, setSpoiled] = useState('');
  const [coordText, setCoordText] = useState(coords ? `${coords.lat.toFixed(4)}, ${coords.lon.toFixed(4)}` : '');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [needSplit, setNeedSplit] = useState(false);
  const [res, setRes] = useState<RescueResponse | null>(null);

  const input = (highlight = false) => ({
    minHeight: SIZE.touch,
    borderWidth: highlight ? 3 : 2,
    borderColor: highlight ? C.highlightBorder : C.border,
    backgroundColor: highlight ? C.highlight : C.bg,
    borderRadius: 8,
    paddingHorizontal: 12,
    fontSize: SIZE.large,
    color: C.text,
    fontFamily: fontFor(lang),
  });

  async function useLocation() {
    const at = await deviceCoords();
    if (!at) return setMessage(t('err_origin_unknown'));
    setCoords(at);
    setCoordText(`${at.lat.toFixed(4)}, ${at.lon.toFixed(4)}`);
  }

  async function submit() {
    setMessage(null);
    const q = num(qty);
    const h = num(hours);
    const at = parseCoords(coordText) ?? coords;
    if (!q || h === null) return setMessage(t('fill_all'));
    if (!at) return setMessage(t('err_origin_unknown'));
    const e = num(edible);
    const sp = num(spoiled);
    const split = edible.trim() !== '' || spoiled.trim() !== '';
    if (split && (e === null || sp === null || Math.abs(e + sp - q) > 0.5)) return setMessage(t('split_sum'));
    setBusy(true);
    try {
      const r = await api.rescue({
        source: 'mandi_unsold',
        crop,
        quantity_kg: q,
        hours_since_harvest: h,
        ...(split ? { edible_kg: e!, spoiled_kg: sp! } : {}),
        origin: { lat: at.lat, lon: at.lon },
        language: lang ?? 'en',
        ...(planId ? { plan_id: planId } : {}),
      });
      setRes(r);
      setNeedSplit(false);
      if (!planId) setPlanId(r.plan_id);
    } catch (err) {
      setNeedSplit(err instanceof ApiError && err.code === 'split_required');
      setMessage(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  const est = res?.split.source === 'estimate' ? ` (${t('estimate')})` : '';
  const outlet = (label: string, kg: number, o: OutletOption | null, none: string) => (
    <View style={s.card}>
      <T color={C.muted}>{label}</T>
      <T bold size={SIZE.number}>
        {t('kg_value', { v: fmtNum(kg) })}
        {est}
      </T>
      {o ? (
        <>
          <T bold size={SIZE.large}>
            {t('send_to', { outlet: L.name(o) })}
          </T>
          <T>{L.typeLabel(o)}</T>
          <T color={C.muted}>{L.km(o)}</T>
          {o.partnered === false && <Banner kind="warn" text={t('not_partnered')} />}
        </>
      ) : (
        <T bold>{none}</T>
      )}
    </View>
  );

  return (
    <Screen>
      <DataBanners fixture={res?._fixture} replayDate={res?.replay_date} />
      <T bold>{t('crop')}</T>
      <View style={s.row}>
        {CROPS.map((c) => (
          <Chip key={c} label={t(`crop_${c}`)} selected={crop === c} onPress={() => setCrop(c)} />
        ))}
      </View>
      <T bold>{`${t('quantity')} (${t('unit_kg')})`}</T>
      <TextInput
        value={qty}
        onChangeText={setQty}
        keyboardType="numeric"
        accessibilityLabel={t('quantity')}
        style={input()}
      />
      <T bold>{t('hours_since_harvest')}</T>
      <TextInput
        value={hours}
        onChangeText={setHours}
        keyboardType="numeric"
        accessibilityLabel={t('hours_since_harvest')}
        style={input()}
      />

      <T bold>{`${t('edible')} (${t('unit_kg')})`}</T>
      <TextInput
        value={edible}
        onChangeText={setEdible}
        keyboardType="numeric"
        accessibilityLabel={t('edible')}
        style={input(needSplit)}
      />
      <T bold>{`${t('spoiled')} (${t('unit_kg')})`}</T>
      <TextInput
        value={spoiled}
        onChangeText={setSpoiled}
        keyboardType="numeric"
        accessibilityLabel={t('spoiled')}
        style={input(needSplit)}
      />
      <T color={C.muted}>{t('split_hint')}</T>

      <T bold>{t('coords')}</T>
      <TextInput
        value={coordText}
        onChangeText={setCoordText}
        keyboardType="numbers-and-punctuation"
        placeholder="12.97, 77.59"
        accessibilityLabel={t('coords')}
        style={input()}
      />
      {coordText.trim() !== '' && !parseCoords(coordText) && <T color={C.errorBg}>{t('coords_invalid')}</T>}
      <Btn kind="secondary" label={t('use_location')} onPress={() => void useLocation()} />

      <Btn label={t('get_recommendation')} onPress={() => void submit()} disabled={busy} />
      {busy && <Loading />}
      {message && <Banner kind="error" text={message} />}

      {res && !busy && (
        <>
          {res.split.edible_kg > 0 &&
            outlet(
              t('edible'),
              res.split.edible_kg,
              res.top,
              // No processor or food bank near: the edible part goes to the Recover outlet too.
              res.recover ? t('second_life_body', { type: L.typeLabel(res.recover) }) : t('no_recover_outlet'),
            )}
          {res.split.spoiled_kg > 0 && outlet(t('spoiled'), res.split.spoiled_kg, res.recover, t('no_recover_outlet'))}
          <T>{res.explanation.text}</T>
          <ImpactRows impact={res.impact} lines="rescue" />
        </>
      )}
    </Screen>
  );
}
