// "Since you started": lifetime totals on this phone (lib/ledger.ts). Every figure is the API's estimate, summed;
// ranges stay ranges. Kept out of landfill = Prevented + Rescued + Recovered (redirected is never added).
import { router } from 'expo-router';
import { View } from 'react-native';
import { fmtNum } from '../i18n';
import type { LedgerTotals } from '../lib/ledger';
import { useSession } from '../lib/session';
import { C, SIZE } from '../lib/theme';
import { Btn, EstNote, Surface, T, fmtDate } from './ui';

// Validated categorical order (dataviz validator, light surface): green, blue, amber.
export const PART_COLORS = { prevented: '#2F855A', rescued: '#2B6CB0', recovered: '#B7791F' } as const;

function Bar({ parts }: { parts: { key: string; n: number; color: string }[] }) {
  const shown = parts.filter((p) => p.n > 0);
  return (
    <View style={{ height: 14, borderRadius: 7, backgroundColor: C.track, overflow: 'hidden', flexDirection: 'row', gap: 2 }}>
      {shown.map((p) => (
        <View key={p.key} style={{ flex: p.n, backgroundColor: p.color }} />
      ))}
    </View>
  );
}

export function Lifetime({ totals }: { totals: LedgerTotals }) {
  const { t } = useSession();
  if (totals.count === 0) {
    return (
      <View style={{ gap: 12 }}>
        <T size={SIZE.large}>{t('ledger_empty')}</T>
        <Btn label={t('new_load')} onPress={() => router.push('/new-load')} />
      </View>
    );
  }
  const k = totals.kept_kg;
  const handled = totals.handled_kg;
  const pct = (v: number) => Math.round((v / handled) * 100);
  const share = handled > 0 ? Math.max(0, Math.min(100, pct(k.mid))) : 0;
  const rangeKg =
    k.low < 0
      ? t('waste_range_loss', { loss: fmtNum(-k.low), high: fmtNum(k.high) })
      : t('waste_range', { low: fmtNum(k.low), high: fmtNum(k.high) });
  const parts = [
    { key: 'prevented', n: Math.max(0, totals.prevented_kg.mid), color: PART_COLORS.prevented },
    { key: 'rescued', n: totals.rescued_kg, color: PART_COLORS.rescued },
    { key: 'recovered', n: totals.recovered_kg, color: PART_COLORS.recovered },
  ];
  const partsTotal = parts.reduce((a, p) => a + p.n, 0);
  const m = totals.extra_rs;

  return (
    <View style={{ gap: 16 }}>
      {totals.since ? (
        <T size={SIZE.label} color={C.muted}>
          {t('count_since', { n: fmtNum(totals.count), date: fmtDate(totals.since.slice(0, 10)) })}
        </T>
      ) : null}

      <View style={{ gap: 4 }}>
        <T size={SIZE.small} color={C.muted}>
          {t('kept_out_of_landfill')}
        </T>
        <T bold size={36} color={C.primary} style={{ lineHeight: 44 }}>
          {t('waste_value', { mid: fmtNum(Math.max(0, k.mid)) })}
        </T>
        <T size={SIZE.small}>{rangeKg}</T>
      </View>

      <Surface style={{ padding: 16, gap: 10 }}>
        <T size={SIZE.small} color={C.muted}>
          {t('share_saved')}
        </T>
        <T bold size={SIZE.number}>{`${share}%`}</T>
        <View
          accessible
          accessibilityLabel={`${t('share_saved')} ${share}%`}
          style={{ height: 14, borderRadius: 7, backgroundColor: C.track, overflow: 'hidden' }}
        >
          <View style={{ width: `${share}%`, height: '100%', backgroundColor: PART_COLORS.prevented, borderRadius: 7 }} />
        </View>
        <T size={SIZE.label} color={C.muted}>
          {t('of_handled', { kg: fmtNum(handled) })}
        </T>
      </Surface>

      <Surface style={{ padding: 16, gap: 6 }}>
        <T size={SIZE.small} color={C.muted}>
          {t('total_money_saved')}
        </T>
        {m ? (
          <>
            <T bold size={SIZE.number}>{`Rs ${fmtNum(Math.round(m.mid))}`}</T>
            <T size={SIZE.label}>{t('money_range', { low: fmtNum(Math.round(m.low)), high: fmtNum(Math.round(m.high)) })}</T>
          </>
        ) : (
          <T color={C.muted}>{t('not_estimated')}</T>
        )}
        <T size={SIZE.label} color={C.muted}>
          {t('money_note')}
        </T>
      </Surface>

      {partsTotal > 0 ? (
        <Surface style={{ padding: 16, gap: 12 }}>
          <T size={SIZE.small} color={C.muted}>
            {t('impact_from')}
          </T>
          <Bar parts={parts} />
          <View style={{ gap: 8 }}>
            {parts.map((p) => (
              <View key={p.key} style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                <View style={{ width: 12, height: 12, borderRadius: 3, backgroundColor: p.color }} />
                <T style={{ flex: 1 }}>{t(p.key as 'prevented' | 'rescued' | 'recovered')}</T>
                <T bold>{`${t('kg_value', { v: fmtNum(p.n) })} · ${Math.round((p.n / partsTotal) * 100)}%`}</T>
              </View>
            ))}
          </View>
        </Surface>
      ) : null}
      <EstNote />
    </View>
  );
}
