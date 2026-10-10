// Confirm: editable fields from the voice parse; low confidence highlights everything, null fields always.
import { router } from 'expo-router';
import { useState } from 'react';
import { View } from 'react-native';
import { Icon } from '../components/Icon';
import { LoadForm } from '../components/LoadForm';
import { Banner, Btn, DataBanners, Loading, Screen, T, useErrorText } from '../components/ui';
import { draftComplete, useRecommend } from '../lib/recommend';
import { useSession, type LoadDraft } from '../lib/session';
import { C, RADIUS, SIZE } from '../lib/theme';

const FIELDS: (keyof LoadDraft)[] = ['crop', 'quantity_kg', 'origin_place', 'harvest'];

export default function ConfirmScreen() {
  const { t, draft, setDraft, voice } = useSession();
  const recommend = useRecommend();
  const errorText = useErrorText();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const lowConfidence = voice?.confidence !== 'high';
  const highlight = lowConfidence ? FIELDS : FIELDS.filter((k) => draft[k] === null);

  async function confirm() {
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

  return (
    <Screen>
      <DataBanners />
      {voice?.transcript ? (
        <View style={{ backgroundColor: C.surfaceLow, borderRadius: RADIUS.field, padding: 16 }}>
          <T size={SIZE.large}>{t('heard', { text: voice.transcript })}</T>
        </View>
      ) : null}
      {highlight.length > 0 && (
        <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 8 }}>
          <Icon name="warning" size={20} color={C.warnText} strokeWidth={2.2} />
          <T bold color={C.warnText} style={{ flexShrink: 1 }}>
            {t('check_highlighted')}
          </T>
        </View>
      )}
      <LoadForm draft={draft} onChange={setDraft} highlight={highlight} showNotHeard />
      {message && <Banner kind="error" text={message} />}
      {busy ? <Loading /> : <Btn label={t('confirm_button')} onPress={() => void confirm()} />}
      <Btn kind="text" label={t('type_instead')} onPress={() => router.replace('/new-load')} />
    </Screen>
  );
}
