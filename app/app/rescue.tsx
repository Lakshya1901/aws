// Unsold stock (Rescue, CLAUDE.md Section 9 Step 5b): a trader at a city mandi logs end-of-day stock.
// Edible part -> processor or food bank; spoiled part -> feed, biogas or compost. Same POST /recommend.
// The edible/spoiled split is optional: empty = the engine proposes it (needs weather at the place);
// without weather (Delhi, Mumbai) the API answers 422 split_required and the trader enters both.
import { useState } from 'react';
import { TextInput, View, type KeyboardTypeOptions } from 'react-native';
import { ApiError, api } from '../api/client';
import { CROPS, isRouterCrop, type CropId, type RescueResponse } from '../api/types';
import { ImpactHeadline, ImpactRows } from '../components/ImpactRows';
import { parseCoords } from '../components/LoadForm';
import { useOutletLabels } from '../components/RecommendationCard';
import { Banner, Btn, Chip, DataBanners, ListRow, Loading, Screen, SectionTitle, Surface, T, Tag, s, useErrorText } from '../components/ui';
import { fmtNum } from '../i18n';
import { deviceCoords } from '../lib/recommend';
import { earnFor, fromImpact, recordLedger } from '../lib/ledger';
import { useSession } from '../lib/session';
import { C, RADIUS, SIZE, fontFor } from '../lib/theme';

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
  const [place, setPlace] = useState('');
  const [coordText, setCoordText] = useState(coords ? `${coords.lat.toFixed(4)}, ${coords.lon.toFixed(4)}` : '');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [needSplit, setNeedSplit] = useState(false);
  const [res, setRes] = useState<RescueResponse | null>(null);
  const [saved, setSaved] = useState(false);

  const field = (
    label: string,
    value: string,
    onChange: (v: string) => void,
    opts: { highlight?: boolean; placeholder?: string; keyboard?: KeyboardTypeOptions; caption?: string } = {},
  ) => (
    <View style={{ gap: 6 }}>
      <T size={SIZE.label} color={C.muted}>
        {label}
      </T>
      <TextInput
        value={value}
        onChangeText={onChange}
        keyboardType={opts.keyboard ?? 'numeric'}
        placeholder={opts.placeholder}
        placeholderTextColor={C.muted}
        accessibilityLabel={label}
        style={{
          height: 56,
          borderWidth: opts.highlight ? 2 : 1,
          borderColor: opts.highlight ? C.warnText : C.outline,
          backgroundColor: opts.highlight ? C.warnBg : 'transparent',
          borderRadius: RADIUS.field,
          paddingHorizontal: 16,
          fontSize: SIZE.large,
          color: C.text,
          fontFamily: fontFor(lang),
        }}
      />
      {opts.caption ? (
        <T size={SIZE.label} color={C.muted}>
          {opts.caption}
        </T>
      ) : null}
    </View>
  );

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
    // Typed coordinates, else the typed city, town or village (resolved by the API), else the device location.
    const at = parseCoords(coordText) ?? (place.trim() ? { lat: null, lon: null } : coords);
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
        origin: { lat: at.lat, lon: at.lon, place: place.trim() || null },
        language: lang ?? 'en',
        ...(planId ? { plan_id: planId } : {}),
      });
      setRes(r);
      setSaved(false);
      setNeedSplit(false);
      if (!planId) setPlanId(r.plan_id);
    } catch (err) {
      setNeedSplit(err instanceof ApiError && err.code === 'split_required');
      setMessage(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  const proposed = res?.split.source === 'estimate' ? res.split : null;
  const estCaption = proposed ? `(${t('estimate')})` : undefined;
  const sumBad = edible.trim() !== '' && spoiled.trim() !== '' && num(qty) !== null && Math.abs((num(edible) ?? 0) + (num(spoiled) ?? 0) - (num(qty) ?? 0)) > 0.5;

  // Edible destination: processor or food bank; if none is in radius it goes to the Recover outlet too.
  const dest = res ? (res.top ?? res.recover) : null;
  const others = res ? res.alternatives.filter((o) => !dest || L.key(o) !== L.key(dest)) : [];
  const estTag = res?.split.source === 'estimate' ? ` (${t('estimate')})` : '';

  return (
    <Screen>
      {res && !busy && (
        <DataBanners fixture={res._fixture} replayDate={res.replay_date} stale={res.data.stale} demoLoads={res.demo_loads} demoLabel={t('demo_stock')} />
      )}

      <View style={{ gap: 6 }}>
        <T size={SIZE.label} color={C.muted}>
          {t('crop')}
        </T>
        <View style={s.row}>
          {CROPS.map((c) => (
            <Chip key={c} label={t(`crop_${c}`)} selected={crop === c} onPress={() => setCrop(c)} />
          ))}
        </View>
      </View>
      {field(`${t('quantity')} (${t('unit_kg')})`, qty, setQty)}
      {field(t('hours_since_harvest'), hours, setHours)}

      <SectionTitle>{t('split_title')}</SectionTitle>
      <View style={{ flexDirection: 'row', gap: 12 }}>
        <View style={{ flex: 1 }}>
          {field(`${t('edible')} (${t('unit_kg')})`, edible, setEdible, {
            highlight: needSplit,
            placeholder: proposed ? fmtNum(proposed.edible_kg) : undefined,
            caption: edible.trim() === '' ? estCaption : undefined,
          })}
        </View>
        <View style={{ flex: 1 }}>
          {field(`${t('spoiled')} (${t('unit_kg')})`, spoiled, setSpoiled, {
            highlight: needSplit,
            placeholder: proposed ? fmtNum(proposed.spoiled_kg) : undefined,
            caption: spoiled.trim() === '' ? estCaption : undefined,
          })}
        </View>
      </View>
      <T size={SIZE.small} color={sumBad ? C.warnText : C.muted}>
        {sumBad ? t('split_sum') : t('split_hint')}
      </T>

      {field(t('place'), place, setPlace, { keyboard: 'default', placeholder: 'Azadpur' })}
      {field(t('coords'), coordText, setCoordText, { keyboard: 'numbers-and-punctuation', placeholder: '12.97, 77.59' })}
      {coordText.trim() !== '' && !parseCoords(coordText) && <T color={C.warnText}>{t('coords_invalid')}</T>}
      <Btn kind="text" icon="pin" label={t('use_location')} onPress={() => void useLocation()} />

      {message && <Banner kind="error" text={message} />}
      {!res && <Btn label={t('get_recommendation')} onPress={() => void submit()} disabled={busy} />}
      {res && !busy && <Btn kind="secondary" label={t('get_recommendation')} onPress={() => void submit()} />}
      {busy && <Loading />}

      {res && !busy && (
        <>
          {res.split.edible_kg > 0 && (
            <View style={{ gap: 8 }}>
              {dest ? (
                <>
                  <T bold size={SIZE.title}>
                    {t('send_to', { outlet: L.name(dest) })}
                  </T>
                  <T bold size={SIZE.number}>
                    {`${t('kg_value', { v: fmtNum(res.split.edible_kg) })}${estTag}`}
                  </T>
                  <View style={[s.row, { alignItems: 'center' }]}>
                    <Tag text={L.typeLabel(dest)} />
                    <T color={C.muted}>{L.km(dest)}</T>
                    {dest.partnered === false && <Tag text={t('not_partnered')} dashed />}
                  </View>
                </>
              ) : (
                <T bold size={SIZE.large}>
                  {t('no_recover_outlet')}
                </T>
              )}
              <T color={C.muted}>{t('rescue_advice')}</T>
            </View>
          )}
          {res.explanation.text ? <T>{res.explanation.text}</T> : null}

          {res.split.spoiled_kg > 0 && (
            <View style={[s.banner, { backgroundColor: C.warnBg, flexDirection: 'column', gap: 4 }]}>
              <T bold color={C.warnText}>
                {`${t('spoiled')}: ${t('kg_value', { v: fmtNum(res.split.spoiled_kg) })}${estTag}`}
              </T>
              {res.recover ? (
                <>
                  <T bold color={C.warnText}>
                    {t('send_to', { outlet: L.name(res.recover) })}
                  </T>
                  <T color={C.warnText}>{`${L.typeLabel(res.recover)}, ${L.km(res.recover)}`}</T>
                </>
              ) : (
                <T bold color={C.warnText}>
                  {t('no_recover_outlet')}
                </T>
              )}
            </View>
          )}

          {(dest || res.recover) && (
            <Btn
              icon={saved ? 'check' : undefined}
              label={saved ? t('saved_record') : t('use_this')}
              disabled={saved}
              onPress={() => {
                // Lifetime record on this phone: kg rescued and recovered for this lot (food banks pay nothing).
                void recordLedger({
                  key: `${res.plan_id}|rescue|${res.crop}|${res.quantity_kg}`,
                  at: new Date().toISOString(),
                  kind: 'rescue',
                  qty_kg: res.quantity_kg,
                  ...fromImpact(res.impact, 'rescue'),
                  earn_rs: dest ? earnFor(dest, res.split.edible_kg) : null,
                });
                setSaved(true);
              }}
            />
          )}

          {others.length > 0 && (
            <>
              <SectionTitle>{t('alternatives')}</SectionTitle>
              <Surface>
                {others.map((o, i) => (
                  <ListRow key={L.key(o)} first={i === 0}>
                    <T bold>{L.name(o)}</T>
                    <T color={C.muted}>{`${L.typeLabel(o)}, ${L.km(o)}`}</T>
                  </ListRow>
                ))}
              </Surface>
            </>
          )}

          <ImpactHeadline impact={res.impact} />
          <ImpactRows impact={res.impact} lines="rescue" />
        </>
      )}
    </Screen>
  );
}
