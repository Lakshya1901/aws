import { NotoSans_400Regular } from '@expo-google-fonts/noto-sans/400Regular';
import { NotoSans_600SemiBold } from '@expo-google-fonts/noto-sans/600SemiBold';
import { NotoSansDevanagari_400Regular } from '@expo-google-fonts/noto-sans-devanagari/400Regular';
import { NotoSansDevanagari_700Bold } from '@expo-google-fonts/noto-sans-devanagari/700Bold';
import { NotoSansBengali_400Regular } from '@expo-google-fonts/noto-sans-bengali/400Regular';
import { NotoSansBengali_700Bold } from '@expo-google-fonts/noto-sans-bengali/700Bold';
import { NotoSansTelugu_400Regular } from '@expo-google-fonts/noto-sans-telugu/400Regular';
import { NotoSansTelugu_700Bold } from '@expo-google-fonts/noto-sans-telugu/700Bold';
import { NotoSansTamil_400Regular } from '@expo-google-fonts/noto-sans-tamil/400Regular';
import { NotoSansTamil_700Bold } from '@expo-google-fonts/noto-sans-tamil/700Bold';
import { NotoSansGujarati_400Regular } from '@expo-google-fonts/noto-sans-gujarati/400Regular';
import { NotoSansGujarati_700Bold } from '@expo-google-fonts/noto-sans-gujarati/700Bold';
import { NotoNaskhArabic_400Regular } from '@expo-google-fonts/noto-naskh-arabic/400Regular';
import { NotoNaskhArabic_700Bold } from '@expo-google-fonts/noto-naskh-arabic/700Bold';
import { NotoSansOriya_400Regular } from '@expo-google-fonts/noto-sans-oriya/400Regular';
import { NotoSansOriya_700Bold } from '@expo-google-fonts/noto-sans-oriya/700Bold';
import { NotoSansMalayalam_400Regular } from '@expo-google-fonts/noto-sans-malayalam/400Regular';
import { NotoSansMalayalam_700Bold } from '@expo-google-fonts/noto-sans-malayalam/700Bold';
import { NotoSansGurmukhi_400Regular } from '@expo-google-fonts/noto-sans-gurmukhi/400Regular';
import { NotoSansGurmukhi_700Bold } from '@expo-google-fonts/noto-sans-gurmukhi/700Bold';
import { NotoSansOlChiki_400Regular } from '@expo-google-fonts/noto-sans-ol-chiki/400Regular';
import { NotoSansOlChiki_700Bold } from '@expo-google-fonts/noto-sans-ol-chiki/700Bold';
import { NotoSansKannada_400Regular } from '@expo-google-fonts/noto-sans-kannada/400Regular';
import { NotoSansKannada_700Bold } from '@expo-google-fonts/noto-sans-kannada/700Bold';
import { useFonts } from 'expo-font';
import { router, Stack } from 'expo-router';
import { Pressable } from 'react-native';
import { Icon } from '../components/Icon';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Loading } from '../components/ui';
import { SessionProvider, useSession } from '../lib/session';
import { C, fontFor } from '../lib/theme';

// Today, Today's plan and Impact are tabs (NavBar): no back arrow, no swipe back between them.
const TAB = { headerBackVisible: false, headerLeft: () => null, gestureEnabled: false, animation: 'none' } as const;

/** Settings on every screen's top bar (icon only, 48 dp). */
function SettingsButton({ label }: { label: string }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={() => router.push('/settings')}
      style={{ width: 48, height: 48, alignItems: 'center', justifyContent: 'center' }}
    >
      <Icon name="settings" size={24} color={C.text} />
    </Pressable>
  );
}

function Nav() {
  const { ready, t, lang } = useSession();
  if (!ready) return <Loading />;
  const fontFamily = fontFor(lang, true);
  // key: a language change remounts the stack (fresh at index -> Today) instead of re-styling every mounted native
  // header with a new script font, which crashed Android on the October 10 phone test.
  return (
    <Stack
      key={lang ?? 'none'}
      screenOptions={{
        // Material 3 top app bar: same surface as the page, no shadow.
        headerStyle: { backgroundColor: C.bg },
        headerShadowVisible: false,
        headerTintColor: C.text,
        headerTitleStyle: { fontSize: 20, fontFamily },
        contentStyle: { backgroundColor: C.bg },
        headerRight: () => <SettingsButton label={t('settings')} />,
      }}
    >
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="language" options={{ title: t('app_name'), headerRight: () => null }} />
      <Stack.Screen name="today" options={{ title: t('today_title'), ...TAB }} />
      <Stack.Screen name="crops" options={{ title: t('other_crop') }} />
      <Stack.Screen name="settings" options={{ title: t('settings'), headerRight: () => null }} />
      <Stack.Screen name="new-load" options={{ title: t('new_load') }} />
      <Stack.Screen name="confirm" options={{ title: t('confirm_title') }} />
      <Stack.Screen name="rescue" options={{ title: t('unsold_stock') }} />
      <Stack.Screen name="recommendation" options={{ title: t('app_name') }} />
      <Stack.Screen name="plan" options={{ title: t('todays_plan'), ...TAB }} />
      <Stack.Screen name="impact" options={{ title: t('impact'), ...TAB }} />
    </Stack>
  );
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    NotoSans_400Regular,
    NotoSans_600SemiBold,
    NotoSansDevanagari_400Regular,
    NotoSansDevanagari_700Bold,
    NotoSansKannada_400Regular,
    NotoSansKannada_700Bold,
    NotoSansBengali_400Regular,
    NotoSansBengali_700Bold,
    NotoSansTelugu_400Regular,
    NotoSansTelugu_700Bold,
    NotoSansTamil_400Regular,
    NotoSansTamil_700Bold,
    NotoSansGujarati_400Regular,
    NotoSansGujarati_700Bold,
    NotoNaskhArabic_400Regular,
    NotoNaskhArabic_700Bold,
    NotoSansOriya_400Regular,
    NotoSansOriya_700Bold,
    NotoSansMalayalam_400Regular,
    NotoSansMalayalam_700Bold,
    NotoSansGurmukhi_400Regular,
    NotoSansGurmukhi_700Bold,
    NotoSansOlChiki_400Regular,
    NotoSansOlChiki_700Bold,
  });
  return (
    <SafeAreaProvider>
      <SessionProvider>
        <StatusBar style="dark" />
        {fontsLoaded || fontError ? <Nav /> : null}
      </SessionProvider>
    </SafeAreaProvider>
  );
}
