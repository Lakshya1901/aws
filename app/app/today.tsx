// Today (Glut Radar): nearby markets for the chosen crop, risk as colour + word + icon.
import * as Location from 'expo-location';
import { Stack, router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, View } from 'react-native';
import { MOCK, api } from '../api/client';
import { CROPS, type RiskResponse } from '../api/types';
import { RiskList } from '../components/RiskList';
import { Icon } from '../components/Icon';
import { Banner, Btn, Chip, DataBanners, Loading, Screen, SectionTitle, T, useErrorText } from '../components/ui';
import { LANG_INFO } from '../i18n';
import { cacheRisk, readCachedRisk, useSession } from '../lib/session';
import { C, RADIUS, SIZE } from '../lib/theme';

export default function TodayScreen() {
  const { t, lang, crop, setCrop, crops, setCrops, cropLabel, coords, setCoords, setUnitBoxKg } = useSession();
  const errorText = useErrorText();
  const [data, setData] = useState<RiskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fromCache, setFromCache] = useState(false);

  // Location once; the radar still works without it.
  useEffect(() => {
    if (coords) return;
    (async () => {
      try {
        const perm = await Location.requestForegroundPermissionsAsync();
        if (!perm.granted) return;
        const pos =
          (await Location.getLastKnownPositionAsync()) ??
          (await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }));
        if (pos) setCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude });
      } catch {}
    })();
  }, [coords, setCoords]);

  // Crop catalogue once (top crops for the chips; every commodity on the Other crop screen).
  useEffect(() => {
    if (crops.length) return;
    api.crops().then((r) => setCrops(r.crops), () => {});
  }, [crops.length, setCrops]);
  const top = crops.length ? crops.filter((c) => c.preload).map((c) => c.crop_id) : [...CROPS];
  const chips = top.includes(crop) ? top : [...top, crop];

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setFromCache(false);
    try {
      const res = await api.risk({ crop, lat: coords?.lat, lon: coords?.lon });
      setData(res);
      setUnitBoxKg(res.unit_box_kg);
      void cacheRisk(crop, res);
    } catch (e) {
      const cached = await readCachedRisk(crop);
      // Never show cached fixture data outside mock mode.
      if (cached && (MOCK || !cached._fixture)) {
        setData(cached);
        setUnitBoxKg(cached.unit_box_kg);
        setFromCache(true);
      } else {
        setData(null);
      }
      setError(errorText(e));
    } finally {
      setLoading(false);
    }
  }, [crop, coords, setUnitBoxKg, errorText]);

  useEffect(() => {
    void load();
  }, [crop, coords]);

  const anyStale = data?.markets.some((m) => m.stale) ?? false;

  return (
    <Screen nav>
      <Stack.Screen
        options={{
          headerRight: () => (
            <Btn
              kind="text"
              icon="globe"
              label={LANG_INFO[lang ?? 'en'].name}
              onPress={() => router.push('/language')}
            />
          ),
        }}
      />
      {!loading && data && (
        <DataBanners fixture={data._fixture} replayDate={data.replay_date} stale={anyStale} />
      )}

      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('new_load')}
        onPress={() => router.push('/new-load')}
        style={({ pressed }) => ({
          minHeight: 80,
          borderRadius: RADIUS.surface,
          backgroundColor: C.primary,
          flexDirection: 'row',
          alignItems: 'center',
          gap: 16,
          paddingHorizontal: 16,
          paddingVertical: 12,
          opacity: pressed ? 0.8 : 1,
        })}
      >
        <View style={{ width: 52, height: 52, borderRadius: 26, backgroundColor: '#FFFFFF', alignItems: 'center', justifyContent: 'center' }}>
          <Icon name="mic" size={28} color={C.primary} />
        </View>
        <View style={{ flex: 1 }}>
          <T bold size={SIZE.large} color={C.primaryText}>
            {t('new_load')}
          </T>
          <T size={SIZE.small} color={C.primaryText}>
            {t('speak')}
          </T>
        </View>
      </Pressable>
      <Btn kind="secondary" label={t('unsold_stock')} onPress={() => router.push('/rescue')} />

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }} style={{ flexGrow: 0 }}>
        {chips.map((c) => (
          <Chip key={c} label={cropLabel(c)} selected={crop === c} onPress={() => setCrop(c)} />
        ))}
        <Chip label={t('other_crop')} selected={false} onPress={() => router.push('/crops')} />
      </ScrollView>

      {loading && <Loading />}
      {!loading && error && (
        <>
          <Banner kind={fromCache ? 'warn' : 'error'} text={fromCache ? t('cached_data') : error} />
          {fromCache && <T>{error}</T>}
          <Btn kind="secondary" label={t('retry')} onPress={() => void load()} />
        </>
      )}
      {!loading && data && (
        <>
          <SectionTitle>{t('markets_near')}</SectionTitle>
          <RiskList markets={data.markets} mode={data.mode} />
        </>
      )}
    </Screen>
  );
}
