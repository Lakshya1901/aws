// Impact Ledger: session totals from GET /impact.
import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { ImpactResponse } from '../api/types';
import { ImpactRows } from '../components/ImpactRows';
import { Banner, Btn, DataBanners, Loading, Screen, T, useErrorText } from '../components/ui';
import { useSession } from '../lib/session';
import { SIZE } from '../lib/theme';

export default function ImpactScreen() {
  const { t, planId } = useSession();
  const errorText = useErrorText();
  const [data, setData] = useState<ImpactResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!planId) return;
    setLoading(true);
    setError(null);
    try {
      setData(await api.impact(planId));
    } catch (e) {
      setError(errorText(e));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Screen>
      <T bold size={SIZE.title}>
        {t('impact_title')}
      </T>
      {!planId && <T size={SIZE.large}>{t('no_plan')}</T>}
      {loading && <Loading />}
      {error && (
        <>
          <Banner kind="error" text={error} />
          <Btn kind="secondary" label={t('retry')} onPress={() => void load()} />
        </>
      )}
      {data && !loading && (
        <>
          <DataBanners fixture={data._fixture} />
          <ImpactRows impact={data} />
        </>
      )}
    </Screen>
  );
}
