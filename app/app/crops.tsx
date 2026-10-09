// Other crop: search every AGMARKNET commodity (GET /crops). A crop whose data is not loaded can be fetched
// (POST /crops/fetch, queued on AWS); the screen polls while open and the farmer can come back later (D24).
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { TextInput, View } from 'react-native';
import { api } from '../api/client';
import type { CropInfo, CropStatus } from '../api/types';
import { Banner, Btn, Loading, Screen, T, s, useErrorText } from '../components/ui';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';

const POLL_MS = 10_000;

export default function CropsScreen() {
  const { t, crops, setCrops, setCrop } = useSession();
  const errorText = useErrorText();
  const [query, setQuery] = useState('');
  const [picked, setPicked] = useState<CropInfo | null>(null);
  const [status, setStatus] = useState<CropStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (crops.length) return;
    api.crops().then((r) => setCrops(r.crops), (e) => setError(errorText(e)));
  }, [crops.length, setCrops, errorText]);

  const pick = async (c: CropInfo) => {
    setPicked(c);
    setStatus(null);
    setError(null);
    try {
      const r = await api.crops(c.crop_id);
      setStatus(r.crops[0]?.status ?? 'available');
    } catch (e) {
      setError(errorText(e));
    }
  };

  // While a fetch is queued, check again every POLL_MS until the data is ready.
  useEffect(() => {
    if (!picked || status !== 'fetching') return;
    const id = setInterval(() => {
      api.crops(picked.crop_id).then((r) => setStatus(r.crops[0]?.status ?? 'available'), () => {});
    }, POLL_MS);
    return () => clearInterval(id);
  }, [picked, status]);

  const fetchData = async () => {
    if (!picked) return;
    setError(null);
    try {
      setStatus((await api.fetchCrop(picked.crop_id)).status);
    } catch (e) {
      setError(errorText(e));
    }
  };

  const show = () => {
    if (!picked) return;
    setCrop(picked.crop_id);
    router.back();
  };

  const q = query.trim().toLowerCase();
  const list = crops.filter((c) => !q || c.name.toLowerCase().includes(q)).slice(0, 40);

  return (
    <Screen>
      <TextInput
        value={query}
        onChangeText={setQuery}
        placeholder={t('search_crop')}
        accessibilityLabel={t('search_crop')}
        style={{
          minHeight: SIZE.touch,
          borderWidth: 2,
          borderColor: C.border,
          borderRadius: 8,
          paddingHorizontal: 12,
          fontSize: SIZE.large,
          color: C.text,
          backgroundColor: C.bg,
        }}
      />
      {error && <Banner kind="error" text={error} />}

      {picked && (
        <View style={s.card}>
          <T bold size={SIZE.title}>
            {picked.name}
          </T>
          {!picked.routing && <T>{t('radar_only')}</T>}
          {status === null && !error && <Loading />}
          {status === 'ready' && <Btn label={t('data_ready')} onPress={show} />}
          {status === 'available' && <Btn label={t('get_data')} onPress={() => void fetchData()} />}
          {status === 'fetching' && <Banner kind="info" text={t('fetching_data')} />}
        </View>
      )}

      {!crops.length && !error && <Loading />}
      {list.map((c) => (
        <Btn
          key={c.crop_id}
          kind={picked?.crop_id === c.crop_id ? 'primary' : 'secondary'}
          label={c.name}
          onPress={() => void pick(c)}
        />
      ))}
    </Screen>
  );
}
