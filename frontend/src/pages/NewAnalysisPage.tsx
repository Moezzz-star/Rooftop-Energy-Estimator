import { PageContainer } from '@/components';
import { AnalysisWizard } from '@/features/wizard';

/** New analysis wizard (sample-path): project -> area -> imagery -> submit. */
export function NewAnalysisPage(): JSX.Element {
  return (
    <PageContainer
      title="New analysis"
      description="Create a rooftop energy analysis from the bundled sample area."
      maxWidth="md"
    >
      <AnalysisWizard />
    </PageContainer>
  );
}
