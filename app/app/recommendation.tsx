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
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';

export default function RecommendationScreen() {
  const { t, lang, current, addLoad } = useSession();
  const L = useOutletLabels();
  const [compareOpen, setCompareOpen] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [used, setUsed] = useState<string | null>(null);
  const player = useRef<AudioPlayer | null>(null);
  const loadId = useMemo(() => `l_${Date.now().toString(36)}`, [current]);

  const res = current?.res;
  const req = current?.req;

  // Polly speaks Hindi and Indian English only. For Kannada, speak the English template from config/copy.
  const speech = useMemo(() => {
    if (!res || !req) return null;
    if (lang === 'hi' || lang === 'en') {
      return res.explanation.language === lang && res.explanation.text
        ? { text: res.explanation.text, language: lang }
        : null;
    }
    let text = `${translate('en', 'send_to', { outlet: res.top.name })}.`;
    if (res.default.outlet_id !== res.top.outlet_id && res.default.arrival_ratio != null) {
      text += ` ${translate('en', 'glut_reason', {
        market: res.default.name,
        ratio: res.default.arrival_ratio.toFixed(1),
        crop: translate('en', `crop_${req.crop}`),
      })}.`;
    }
    return { text, language: 'en' as const };
  }, [res, req, lang]);

  // Fetch audio up front; if /speak fails, Listen stays hidden.
  useEffect(() => {
    setAudioUrl(null);
    if (!speech) return;
    let cancelled = false;
    api
      .speak(speech)
      .then((r) => !cancelled && setAudioUrl(r.audio_url))
      .catch(() => {});
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
      override: outlet.outlet_id !== res.top.outlet_id,
    });
    setUsed(outlet.outlet_id);
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
  const alternatives = res.alternatives.slice(0, 2);

  return (
    <Screen>
      <DataBanners fixture={res._fixture} replayDate={res.replay_date} stale={res.data.stale} demoLoads={res.demo_loads} />

      {advice && res.harvest_cost_rs_per_kg != null && (
        <Banner
          kind="warn"
          text={t(advice, {
            low: fmtRs(res.top.net_rs_per_kg.low),
            high: fmtRs(res.top.net_rs_per_kg.high),
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
        used={used === res.top.outlet_id}
      />

      {alternatives.length > 0 && (
        <T bold size={SIZE.title}>
          {t('alternatives')}
        </T>
      )}
      {alternatives.map((o) => (
        <View key={o.outlet_id} style={s.card}>
          <T bold size={SIZE.large}>
            {o.name}
          </T>
          <View style={s.row}>
            {o.type === 'mandi' ? <RiskBadge level={o.risk_level} /> : <T bold>{L.typeLabel(o)}</T>}
            {o.partnered === false && <Banner kind="warn" text={t('not_partnered')} />}
          </View>
          <T bold size={SIZE.number}>
            {`${L.earn(o)} (${t('estimate')})`}
          </T>
          <T color={C.muted}>{L.km(o)}</T>
          <Btn kind="secondary" label={t('send_here')} onPress={() => use(o)} disabled={used === o.outlet_id} />
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
