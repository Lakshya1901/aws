// New load: hold-to-speak mic (upload -> presigned PUT -> parse -> Confirm), typed form as fallback.
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { api } from '../api/client';
import { LoadForm } from '../components/LoadForm';
import { MicButton } from '../components/MicButton';
import { Banner, Btn, DataBanners, Screen, T, useErrorText } from '../components/ui';
import { draftComplete, useRecommend } from '../lib/recommend';
import { LANG_INFO } from '../i18n';
import { EMPTY_DRAFT, useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';

const CONTENT_TYPE = 'audio/mp4'; // m4a (AAC)

export default function NewLoadScreen() {
  const { t, lang, crop, coords, draft, setDraft, setVoice, canRoute } = useSession();
  const recommend = useRecommend();
  const errorText = useErrorText();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  // Fresh draft each time the screen opens.
  useEffect(() => {
    setDraft({ ...EMPTY_DRAFT, crop: canRoute(crop) ? crop : null, lat: coords?.lat ?? null, lon: coords?.lon ?? null });
    setReady(true);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function onRecorded(uri: string) {
    setBusy(true);
    setMessage(null);
    try {
      const language = lang ?? 'en';
      const slot = await api.voiceUpload({ language, content_type: CONTENT_TYPE });
      await api.putAudio(slot.upload_url, uri, CONTENT_TYPE);
      const parsed = await api.voiceParse({ audio_key: slot.audio_key, language });
      setVoice(parsed);
      setDraft({
        ...draft,
        crop: parsed.fields.crop,
        quantity_kg: parsed.fields.quantity_kg,
        origin_place: parsed.fields.origin_place,
        harvest: parsed.fields.harvest,
      });
      router.push('/confirm');
    } catch {
      setMessage(t('parse_failed'));
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (!draftComplete(draft)) {
      setMessage(t('fill_all'));
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await recommend(draft);
    } catch (e) {
      setMessage(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  // Voice input only where Amazon Transcribe supports the language; the typed form always works.
  const voice = LANG_INFO[lang ?? 'en'].voice;

  return (
    <Screen>
      <DataBanners />
      {voice && (
      <MicButton
        disabled={busy}
        onRecorded={(uri) => void onRecorded(uri)}
        onFailed={(r) => setMessage(r === 'denied' ? t('mic_denied') : t('parse_failed'))}
      />
      )}
      {busy && (
        <View style={{ alignItems: 'center' }}>
          <ActivityIndicator size="large" color={C.primary} />
          <T bold style={{ textAlign: 'center' }}>
            {t('processing')}
          </T>
        </View>
      )}
      {message && <Banner kind={message === t('fill_all') || message === t('parse_failed') || message === t('mic_denied') ? 'warn' : 'error'} text={message} />}

      {voice && (
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        <View style={{ flex: 1, height: 1, backgroundColor: C.divider }} />
        <T size={SIZE.small} color={C.muted} style={{ textAlign: 'center', flexShrink: 1 }}>
          {t('or_type')}
        </T>
        <View style={{ flex: 1, height: 1, backgroundColor: C.divider }} />
      </View>
      )}
      {ready && <LoadForm draft={draft} onChange={setDraft} />}
      <Btn label={t('get_recommendation')} onPress={() => void submit()} disabled={busy} />
    </Screen>
  );
}
