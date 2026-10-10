import { NotoSans_400Regular } from '@expo-google-fonts/noto-sans/400Regular';
import { NotoSans_600SemiBold } from '@expo-google-fonts/noto-sans/600SemiBold';
import { NotoSansDevanagari_400Regular } from '@expo-google-fonts/noto-sans-devanagari/400Regular';
import { NotoSansDevanagari_700Bold } from '@expo-google-fonts/noto-sans-devanagari/700Bold';
import { NotoSansKannada_400Regular } from '@expo-google-fonts/noto-sans-kannada/400Regular';
import { NotoSansKannada_700Bold } from '@expo-google-fonts/noto-sans-kannada/700Bold';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Loading } from '../components/ui';
import { SessionProvider, useSession } from '../lib/session';
import { C, fontFor } from '../lib/theme';

// Today, Today's plan and Impact are tabs (NavBar): no back arrow, no swipe back between them.
const TAB = { headerBackVisible: false, headerLeft: () => null, gestureEnabled: false, animation: 'none' } as const;

function Nav() {
  const { ready, t, lang } = useSession();
  if (!ready) return <Loading />;
  const fontFamily = fontFor(lang, true);
  return (
    <Stack
      screenOptions={{
        // Material 3 top app bar: same surface as the page, no shadow.
        headerStyle: { backgroundColor: C.bg },
        headerShadowVisible: false,
        headerTintColor: C.text,
        headerTitleStyle: { fontSize: 20, fontFamily },
        contentStyle: { backgroundColor: C.bg },
      }}
    >
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="language" options={{ title: t('app_name') }} />
      <Stack.Screen name="today" options={{ title: t('today_title'), ...TAB }} />
      <Stack.Screen name="crops" options={{ title: t('other_crop') }} />
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
