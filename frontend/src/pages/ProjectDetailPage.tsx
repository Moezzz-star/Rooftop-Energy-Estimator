import { useParams, Link as RouterLink } from 'react-router-dom';
import { Button } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import ScienceIcon from '@mui/icons-material/Science';
import { PageContainer, LoadingState, ErrorState, EmptyState } from '@/components';
import { useProjectAnalyses, AnalysisList } from '@/features/analyses';
import { ROUTES } from '@/routes/paths';

/** Project detail: list the project's analyses and launch new ones. */
export function ProjectDetailPage(): JSX.Element {
  const { projectId } = useParams<{ projectId: string }>();
  const analysesQuery = useProjectAnalyses(projectId, { ordering: '-created_at' });
  const newAnalysisTo = projectId
    ? `${ROUTES.newAnalysis}?project=${projectId}`
    : ROUTES.newAnalysis;

  return (
    <PageContainer
      title="Project"
      description="Analyses in this project."
      actions={
        <Button
          variant="contained"
          color="secondary"
          startIcon={<AddIcon />}
          component={RouterLink}
          to={newAnalysisTo}
        >
          New analysis
        </Button>
      }
    >
      {analysesQuery.isPending && <LoadingState label="Loading analyses…" />}

      {analysesQuery.isError && (
        <ErrorState
          message={analysesQuery.error.message}
          onRetry={() => void analysesQuery.refetch()}
        />
      )}

      {analysesQuery.isSuccess &&
        (analysesQuery.data.results.length === 0 ? (
          <EmptyState
            icon={<ScienceIcon fontSize="inherit" />}
            title="No analyses yet"
            description="Start a new analysis from the bundled sample area."
            action={
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                component={RouterLink}
                to={newAnalysisTo}
              >
                New analysis
              </Button>
            }
          />
        ) : (
          <AnalysisList analyses={analysesQuery.data.results} />
        ))}
    </PageContainer>
  );
}
