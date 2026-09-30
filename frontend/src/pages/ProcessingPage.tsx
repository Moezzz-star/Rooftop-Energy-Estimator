import { useParams } from 'react-router-dom';
import { PageContainer, ErrorState } from '@/components';
import { ProcessingView } from '@/features/analyses';

/** Live processing view: polls the real job and renders pipeline stages. */
export function ProcessingPage(): JSX.Element {
  const { analysisId } = useParams<{ analysisId: string }>();
  return (
    <PageContainer title="Processing" maxWidth="md">
      {analysisId ? (
        <ProcessingView analysisId={analysisId} />
      ) : (
        <ErrorState title="Missing analysis" message="No analysis id was provided." />
      )}
    </PageContainer>
  );
}
