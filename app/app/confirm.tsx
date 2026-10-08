// Confirm: editable fields from the voice parse; low confidence highlights everything, null fields always.
import { useState } from 'react';
import { LoadForm } from '../components/LoadForm';
import { Banner, Btn, DataBanners, Loading, Screen, T, useErrorText } from '../components/ui';
import { draftComplete, useRecommend } from '../lib/recommend';
import { useSession, type LoadDraft } from '../lib/session';
import { SIZE } from '../lib/theme';

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
      <T bold size={SIZE.title}>
        {t('confirm_title')}
      </T>
      {voice?.transcript ? <T size={SIZE.large}>{t('heard', { text: voice.transcript })}</T> : null}
      {highlight.length > 0 && <Banner kind="warn" text={t('check_highlighted')} />}
      <LoadForm draft={draft} onChange={setDraft} highlight={highlight} />
      {message && <Banner kind="error" text={message} />}
      {busy ? <Loading /> : <Btn label={t('confirm_button')} onPress={() => void confirm()} />}
    </Screen>
  );
}
