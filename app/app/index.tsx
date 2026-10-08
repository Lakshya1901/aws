import { Redirect } from 'expo-router';
import { useSession } from '../lib/session';

export default function Index() {
  const { lang } = useSession();
  return <Redirect href={lang ? '/today' : '/language'} />;
}
