// "When was it harvested?" as day chips (today, yesterday, 2-5 days ago); the API turns days into hours since harvest
// for the spoilage estimate (0 days = harvested_today_hours, an assumption). Farmers know the day, not the hours.
import { View } from 'react-native';
import { useSession } from '../lib/session';
import { Chip, s } from './ui';

const DAYS = [0, 1, 2, 3, 4, 5];

export function HarvestAge({ days, onSelect }: { days: number | null; onSelect: (d: number) => void }) {
  const { t } = useSession();
  const label = (d: number) => (d === 0 ? t('age_today') : d === 1 ? t('age_yesterday') : t('age_days', { n: d }));
  return (
    <View style={s.row}>
      {DAYS.map((d) => (
        <Chip key={d} label={label(d)} selected={days === d} onPress={() => onSelect(d)} />
      ))}
    </View>
  );
}
