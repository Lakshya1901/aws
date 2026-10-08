// Recommendation: the card, two alternatives, "Why not <default>?", Listen, Use this (overrides allowed).
import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from 'expo-audio';
import { router } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { View } from 'react-native';
import { api } from '../api/client';
import type { OutletOption } from '../api/types';
import { CompareSheet } from '../components/CompareSheet';
import { RecommendationCard, useOutletLabels } from '../components/RecommendationCard';
import { Banner, Btn, DataBanners, RiskBadge, Screen, T, s } from '../components/ui';
import { fmtRs, translate } from '../i18n';
import { ratioDriven } from '../lib/recommend';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';

export default function RecommendationScreen() {
  const { t, lang, current, addLoad } = useSession();
  const L = useOutletLabels();
  const [compareOpen, setCompareOpen] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [used, setUsed] = useState<string | null>(null); // L.key of the outlet chosen
  const player = useRef<AudioPlayer | null>(null);
  const loadId = useMemo(() => `l_${Date.now().toString(36)}`, [current]);

  const res = current?.res;
  const req = current?.req;

  // Polly speaks Hindi and Indian English only. For Kannada, speak an English sentence from config/copy,
  // built like the backend template: the arrival multiple only when it drives the default's risk (D10),
  // else the default's 3-day price drop; then the net-value comparison.
  const speech = useMemo(() => {
    if (!res || !req) return null;
    if (lang === 'hi' || lang === 'en') {
      return res.explanation.language === lang && res.explanation.text
        ? { text: res.explanation.text, language: lang }
        : null;
    }
    const { top, default: d } = res;
    const en = (o: OutletOption) => o.name ?? translate('en', `type_${o.type}`);
    const parts = [top.type === 'hold' ? translate('en', 'hold_title') : translate('en', 'send_to', { outlet: en(top) })];
    if ((d.outlet_id ?? d.type) !== (top.outlet_id ?? top.type)) {
      if (ratioDriven(d) && d.arrival_ratio != null) {
        parts.push(
          translate('en', 'glut_reason', {
            market: en(d),
            ratio: d.arrival_ratio.toFixed(1),
            crop: translate('en', `crop_${req.crop}`).toLowerCase(),
          }),
        );
      } else if ((d.risk_level === 'watch' || d.risk_level === 'glut') && d.price_change_3d != null && d.price_change_3d < 0) {
        parts.push(`${en(d)}: ${translate('en', 'change_3d', { change: Math.round(d.price_change_3d * 100) })}`);
      }
      if (d.net_rs_per_kg) {
        parts.push(
          translate('en', 'default_compare', {
            market: en(d),
            low: fmtRs(d.net_rs_per_kg.low),
            high: fmtRs(d.net_rs_per_kg.high),
          }),
        );
      }
    }
    return { text: `${parts.join('. ')}.`, language: 'en' as const };
  }, [res, req, lang]);

  // Fetch audio up front; if /speak fails (502, or 422 speak_language_unsupported), Listen stays hidden.
  useEffect(() => {
    setAudioUrl(null);
    if (!speech) return;
    let cancelled = false;
    api
      .speak(speech)
      .then((r) => !cancelled && setAudioUrl(r.audio_url))
      .catch(() => {}); // the text stays on screen; no audio
    return () => {
      cancelled = true;
    };
  }, [speech]);

  useEffect(() => () => player.current?.remove(), []);

  async function listen() {
    if (!audioUrl) return;
    try {
      await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: false });
      player.current?.remove();
      player.current = createAudioPlayer(audioUrl);
      player.current.play();
    } catch {
      setAudioUrl(null);
    }
  }

  function use(outlet: OutletOption) {
    if (!req || !res) return;
    addLoad({
      load_id: loadId,
      crop: req.crop,
      quantity_kg: req.quantity_kg,
      origin: req.origin,
      harvest: req.harvest,
      chosen_outlet_id: outlet.outlet_id,
      override: L.key(outlet) !== L.key(res.top),
    });
    setUsed(L.key(outlet));
    router.push('/plan');
  }

  if (!res || !req) {
    return (
      <Screen>
        <T>{t('plan_empty')}</T>
        <Btn label={t('new_load')} onPress={() => router.replace('/new-load')} />
      </Screen>
    );
  }

  const advice = res.advice;
  // Alternatives may repeat the default market; it is reachable through "Why not".
  const alternatives = res.alternatives.filter((o) => L.key(o) !== L.key(res.default)).slice(0, 2);
  // Advice compares the best fresh market with the harvest cost (top may be hold or Second Life).
  const bestFresh = [res.top, res.default, ...res.alternatives]
    .filter((o) => o.type === 'mandi' && o.net_rs_per_kg)
    .map((o) => o.net_rs_per_kg!)
    .sort((a, b) => b.mid - a.mid)[0];

  return (
    <Screen>
      <DataBanners fixture={res._fixture} replayDate={res.replay_date} stale={res.data.stale} demoLoads={res.demo_loads} />

      {advice && bestFresh && (
        <Banner
          kind="warn"
          text={t(advice, {
            low: fmtRs(bestFresh.low),
            high: fmtRs(bestFresh.high),
            cost: fmtRs(res.harvest_cost_rs_per_kg),
          })}
        />
      )}

      <RecommendationCard
        req={req}
        res={res}
        onWhyNot={() => setCompareOpen(true)}
        onListen={audioUrl ? () => void listen() : null}
        listenNote={lang === 'kn' ? t('listen_lang_note') : null}
        onUse={() => use(res.top)}
        used={used === L.key(res.top)}
      />

      {alternatives.length > 0 && (
        <T bold size={SIZE.title}>
          {t('alternatives')}
        </T>
      )}
      {alternatives.map((o) => (
        <View key={L.key(o)} style={s.card}>
          <T bold size={SIZE.large}>
            {L.name(o)}
          </T>
          <View style={s.row}>
            {o.type === 'mandi' ? <RiskBadge level={o.risk_level} /> : <T bold>{L.typeLabel(o)}</T>}
            {o.partnered === false && <Banner kind="warn" text={t('not_partnered')} />}
          </View>
          <T bold size={SIZE.number}>
            {o.net_rs_per_kg ? `${L.earn(o)} (${t('estimate')})` : L.earn(o)}
          </T>
          <T color={C.muted}>{L.km(o)}</T>
          <Btn kind="secondary" label={t('send_here')} onPress={() => use(o)} disabled={used === L.key(o)} />
        </View>
      ))}

      <CompareSheet
        visible={compareOpen}
        onClose={() => setCompareOpen(false)}
        dflt={res.default}
        top={res.top}
        quantityKg={req.quantity_kg}
        onUseDefault={() => {
          setCompareOpen(false);
          use(res.default);
        }}
      />
    </Screen>
  );
}
