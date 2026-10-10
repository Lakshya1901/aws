// Recommendation: the card, two alternatives, "Why not <default>?", Listen, Use this (overrides allowed).
import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from 'expo-audio';
import { Stack, router } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import { View } from 'react-native';
import { api } from '../api/client';
import type { OutletOption } from '../api/types';
import { CompareSheet } from '../components/CompareSheet';
import { RecommendationCard, useOutletLabels } from '../components/RecommendationCard';
import { Banner, Btn, DataBanners, ListRow, Screen, SectionTitle, Surface, Tag, T } from '../components/ui';
import { fmtNum, fmtRs, translate } from '../i18n';
import { ratioDriven } from '../lib/recommend';
import { extraOver, fromImpact, recordLedger } from '../lib/ledger';
import { useSession } from '../lib/session';
import { C, RISK, SIZE } from '../lib/theme';

export default function RecommendationScreen() {
  const { t, lang, current, addLoad, cropLabel, crops } = useSession();
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
            crop: (crops.find((c) => c.crop_id === req.crop)?.names?.en ?? req.crop).toLowerCase(),
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
    const isTop = L.key(outlet) === L.key(res.top);
    // Lifetime record on this phone; waste avoided is computed for the recommended outlet only.
    void recordLedger({
      key: `${res.plan_id}|${loadId}`,
      at: new Date().toISOString(),
      kind: 'farm',
      qty_kg: req.quantity_kg,
      ...fromImpact(res.impact, 'farm'),
      prevented_kg: isTop ? res.impact.waste_avoided_kg : null,
      extra_rs: extraOver(outlet, res.default, req.quantity_kg),
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
  // Only choosable alternatives: not the default; mandis must be fresh with a known risk. Second Life always.
  const others = res.alternatives.filter((o) => L.key(o) !== L.key(res.default));
  const choosable = (o: OutletOption) => o.type !== 'mandi' || (o.stale !== true && o.risk_level != null);
  const alternatives = others.filter(choosable).slice(0, 2);
  const filteredOut = others.filter((o) => o.type === 'mandi' && !choosable(o)).length;
  // Advice compares the best fresh market with the harvest cost (top may be hold or Second Life).
  const bestFresh = [res.top, res.default, ...res.alternatives]
    .filter((o) => o.type === 'mandi' && o.net_rs_per_kg)
    .map((o) => o.net_rs_per_kg!)
    .sort((a, b) => b.mid - a.mid)[0];

  return (
    <Screen>
      <Stack.Screen options={{ title: t('load_line', { qty: fmtNum(req.quantity_kg), crop: cropLabel(req.crop) }) }} />
      <DataBanners fixture={res._fixture} replayDate={res.replay_date} stale={res.data.stale} demoLoads={res.demo_loads} pricesDate={res.data.prices_date} />

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
        listenNote={lang !== 'hi' && lang !== 'en' ? t('listen_lang_note') : null}
        onUse={() => use(res.top)}
        used={used === L.key(res.top)}
      />

      {alternatives.length > 0 && (
        <View style={{ gap: 8 }}>
          <SectionTitle>{t('alternatives')}</SectionTitle>
          <Surface>
            {alternatives.map((o, i) => (
              <ListRow key={L.key(o)} first={i === 0} style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <View style={{ flex: 1, gap: 2 }}>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
                    <T bold>{L.name(o)}</T>
                    <T size={SIZE.small} color={C.muted}>
                      {L.km(o)}
                    </T>
                    {o.partnered === false && <Tag dashed text={t('not_partnered')} />}
                  </View>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                    {o.type === 'mandi' ? (
                      <T bold size={SIZE.label} color={RISK[o.risk_level ?? 'none'].word}>
                        {o.risk_level ? t(`risk_${o.risk_level}`) : t('risk_not_reported')}
                      </T>
                    ) : (
                      <T size={SIZE.label} color={C.muted}>
                        {L.typeLabel(o)}
                      </T>
                    )}
                    <T size={SIZE.label} color={C.muted}>
                      {`· ${L.earn(o)}`}
                    </T>
                  </View>
                </View>
                <Btn kind="text" label={t('send_here')} onPress={() => use(o)} disabled={used === L.key(o)} />
              </ListRow>
            ))}
          </Surface>
          {filteredOut > 0 && (
            <T size={SIZE.label} color={C.muted}>
              {t('not_advised', { n: filteredOut })}
            </T>
          )}
        </View>
      )}

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
