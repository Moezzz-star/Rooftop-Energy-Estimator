import { useParams } from 'react-router-dom';
import { PageContainer, ErrorState } from '@/components';
import { ResultsView } from '@/features/results';

/** Results screen: zone summary, roof map, buildings table + solar detail. */
export function ResultsPage(): JSX.Element {
  const { analysisId } = useParams<{ analysisId: string }>();
  return (
    <PageContainer title="Results" maxWidth="lg">
      {analysisId ? (
        <ResultsView analysisId={analysisId} />
      ) : (
        <ErrorState title="Missing analysis" message="No analysis id was provided." />
      )}
    </PageContainer>
  );
}
