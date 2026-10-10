// Settings: language, data (live prices for today, or the saved demo glut day, D34), and the crops this farmer sells
// ("My crops", kept on the phone). My crops show first in the crop chips of New load, Unsold stock and Today; every
// crop with a routing profile can be added (D33).
import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';
import { Icon } from '../components/Icon';
import { ListRow, Loading, Screen, SectionTitle, Surface, T } from '../components/ui';
import { LANG_INFO } from '../i18n';
import { useSession } from '../lib/session';
import { C, RADIUS, SIZE } from '../lib/theme';

export default function SettingsScreen() {
  const { t, lang, crops, myCrops, setMyCrops, cropLabel, dataMode, setDataMode } = useSession();
  const [query, setQuery] = useState('');

  const toggle = (c: string) =>
    setMyCrops(myCrops.includes(c) ? (myCrops.length > 1 ? myCrops.filter((x) => x !== c) : myCrops) : [...myCrops, c]);

  const q = query.trim().toLowerCase();
  const routable = crops
    .filter((c) => c.routing)
    .filter((c) => !q || cropLabel(c.crop_id).toLowerCase().includes(q) || c.name.toLowerCase().includes(q))
    .sort((a, b) => Number(myCrops.includes(b.crop_id)) - Number(myCrops.includes(a.crop_id)) || b.markets - a.markets);

  return (
    <Screen>
      <SectionTitle>{t('change_language')}</SectionTitle>
      <Surface>
        <Pressable accessibilityRole="button" onPress={() => router.push('/language')}>
          <ListRow first style={{ minHeight: 56, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
              <Icon name="globe" size={22} color={C.muted} />
              <T bold size={SIZE.large}>
                {LANG_INFO[lang ?? 'en'].name}
              </T>
            </View>
            <Icon name="chevron" size={22} color={C.muted} />
          </ListRow>
        </Pressable>
      </Surface>

      <SectionTitle>{t('data_source')}</SectionTitle>
      <T color={C.muted}>{t('data_hint')}</T>
      <Surface>
        {(['live', 'demo'] as const).map((m, i) => (
          <Pressable
            key={m}
            accessibilityRole="radio"
            accessibilityState={{ checked: dataMode === m }}
            onPress={() => setDataMode(m)}
          >
            <ListRow first={i === 0} style={{ minHeight: 56, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <T bold={dataMode === m} style={{ flexShrink: 1 }}>
                {t(m === 'live' ? 'data_live' : 'data_demo')}
              </T>
              {dataMode === m && <Icon name="check" size={22} color={C.primary} strokeWidth={2.6} />}
            </ListRow>
          </Pressable>
        ))}
      </Surface>

      <SectionTitle>{t('my_crops')}</SectionTitle>
      <T color={C.muted}>{t('my_crops_hint')}</T>
      <TextInput
        value={query}
        onChangeText={setQuery}
        placeholder={t('search_crop')}
        placeholderTextColor={C.muted}
        accessibilityLabel={t('search_crop')}
        style={{
          minHeight: SIZE.touch,
          borderWidth: 1,
          borderColor: C.outline,
          borderRadius: RADIUS.field,
          paddingHorizontal: 12,
          fontSize: SIZE.base,
          color: C.text,
          backgroundColor: C.surface,
        }}
      />
      {!crops.length && <Loading />}
      {routable.length > 0 && (
        <Surface>
          {routable.map((c, i) => {
            const on = myCrops.includes(c.crop_id);
            return (
              <Pressable
                key={c.crop_id}
                accessibilityRole="checkbox"
                accessibilityState={{ checked: on }}
                onPress={() => toggle(c.crop_id)}
              >
                <ListRow first={i === 0} style={{ minHeight: 56, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                  <T bold={on} style={{ flexShrink: 1 }}>
                    {cropLabel(c.crop_id)}
                  </T>
                  {on && <Icon name="check" size={22} color={C.primary} strokeWidth={2.6} />}
                </ListRow>
              </Pressable>
            );
          })}
        </Surface>
      )}
    </Screen>
  );
}
