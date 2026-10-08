import { router } from 'expo-router';
import { View } from 'react-native';
import type { Lang } from '../api/types';
import { Btn, Screen, T } from '../components/ui';
import { LANGS, translate } from '../i18n';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';

export default function LanguageScreen() {
  const { setLang, lang } = useSession();

  function pick(l: Lang) {
    const first = lang === null;
    setLang(l);
    if (first) router.replace('/today');
    else router.back();
  }

  return (
    <Screen>
      {LANGS.map((l) => (
        <T key={l} forLang={l} bold size={SIZE.large}>
          {translate(l, 'choose_language')}
        </T>
      ))}
      <View style={{ gap: 16, marginTop: 8 }}>
        {LANGS.map((l) => (
          <Btn
            key={l}
            forLang={l}
            label={translate(l, `lang_${l}`)}
            onPress={() => pick(l)}
            kind={lang === l ? 'primary' : 'secondary'}
            style={{ minHeight: 72 }}
          />
        ))}
      </View>
      {/* Settings note: Polly offers Hindi and Indian English voices only. */}
      <View style={{ marginTop: 16, gap: 6 }}>
        {LANGS.map((l) => (
          <T key={l} forLang={l} color={C.muted}>
            {translate(l, 'voice_note')}
          </T>
        ))}
      </View>
    </Screen>
  );
}
