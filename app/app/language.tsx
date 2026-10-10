import { router } from 'expo-router';
import { Pressable, View } from 'react-native';
import type { Lang } from '../api/types';
import { Icon } from '../components/Icon';
import { ListRow, Screen, Surface, T } from '../components/ui';
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
      <View style={{ gap: 4 }}>
        {LANGS.map((l) => (
          <T key={l} forLang={l} bold size={SIZE.large}>
            {translate(l, 'choose_language')}
          </T>
        ))}
      </View>
      <Surface>
        {LANGS.map((l, i) => (
          <Pressable key={l} accessibilityRole="button" accessibilityState={{ selected: lang === l }} onPress={() => pick(l)}>
            <ListRow first={i === 0} style={{ minHeight: 64, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <T forLang={l} bold size={SIZE.large}>
                {translate(l, `lang_${l}`)}
              </T>
              {lang === l && <Icon name="check" size={24} color={C.primary} strokeWidth={2.6} />}
            </ListRow>
          </Pressable>
        ))}
      </Surface>
      {/* Settings note: Polly offers Hindi and Indian English voices only. */}
      <View style={{ gap: 6 }}>
        {LANGS.map((l) => (
          <T key={l} forLang={l} color={C.muted} size={SIZE.small}>
            {translate(l, 'voice_note')}
          </T>
        ))}
      </View>
    </Screen>
  );
}
