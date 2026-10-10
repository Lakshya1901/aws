// Language: English plus India's 20 most spoken languages, each in its own script with its English name.
import { router } from 'expo-router';
import { Pressable, View } from 'react-native';
import type { Lang } from '../api/types';
import { Icon } from '../components/Icon';
import { ListRow, Screen, Surface, T } from '../components/ui';
import { LANG_INFO, LANGS, translate } from '../i18n';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';

export default function LanguageScreen() {
  const { setLang, lang } = useSession();

  // The stack remounts on a language change (app/_layout.tsx) and opens Today.
  function pick(l: Lang) {
    if (l !== lang) setLang(l);
    else router.back();
  }

  const shown: Lang[] = lang && lang !== 'en' ? ['en', lang] : ['en', 'hi'];

  return (
    <Screen>
      <View style={{ gap: 4 }}>
        {shown.map((l) => (
          <T key={l} forLang={l} bold size={SIZE.large}>
            {translate(l, 'choose_language')}
          </T>
        ))}
      </View>
      <Surface>
        {LANGS.map((l, i) => (
          <Pressable key={l} accessibilityRole="button" accessibilityState={{ selected: lang === l }} onPress={() => pick(l)}>
            <ListRow first={i === 0} style={{ minHeight: 64, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <View style={{ flexShrink: 1 }}>
                <T forLang={l} bold size={SIZE.large}>
                  {LANG_INFO[l].name}
                </T>
                {l !== 'en' && (
                  <T forLang="en" size={SIZE.label} color={C.muted}>
                    {LANG_INFO[l].english}
                  </T>
                )}
              </View>
              {lang === l && <Icon name="check" size={24} color={C.primary} strokeWidth={2.6} />}
            </ListRow>
          </Pressable>
        ))}
      </Surface>
      {/* Settings note: Polly offers Hindi and Indian English voices only. */}
      <View style={{ gap: 6 }}>
        {shown.map((l) => (
          <T key={l} forLang={l} color={C.muted} size={SIZE.small}>
            {translate(l, 'voice_note')}
          </T>
        ))}
      </View>
    </Screen>
  );
}
