import { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Button, Stack } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import { PageContainer, LoadingState, ErrorState, EmptyState } from '@/components';
import { useProjects, ProjectList, CreateProjectDialog } from '@/features/projects';
import { ROUTES } from '@/routes/paths';

/** Authenticated landing page: project list, create project, start analysis. */
export function DashboardPage(): JSX.Element {
  const [dialogOpen, setDialogOpen] = useState(false);
  const projectsQuery = useProjects({ ordering: '-created_at' });

  const openDialog = (): void => setDialogOpen(true);
  const closeDialog = (): void => setDialogOpen(false);

  return (
    <PageContainer
      title="Dashboard"
      description="Manage your projects and rooftop energy analyses."
      actions={
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" startIcon={<AddIcon />} onClick={openDialog}>
            New project
          </Button>
          <Button
            variant="contained"
            color="secondary"
            component={RouterLink}
            to={ROUTES.newAnalysis}
          >
            New analysis
          </Button>
        </Stack>
      }
    >
      {projectsQuery.isPending && <LoadingState label="Loading projects…" />}

      {projectsQuery.isError && (
        <ErrorState
          message={projectsQuery.error.message}
          onRetry={() => void projectsQuery.refetch()}
        />
      )}

      {projectsQuery.isSuccess &&
        (projectsQuery.data.results.length === 0 ? (
          <EmptyState
            icon={<FolderOpenIcon fontSize="inherit" />}
            title="No projects yet"
            description="Create your first project to organize rooftop energy analyses."
            action={
              <Button variant="contained" startIcon={<AddIcon />} onClick={openDialog}>
                New project
              </Button>
            }
          />
        ) : (
          <ProjectList projects={projectsQuery.data.results} />
        ))}

      <CreateProjectDialog open={dialogOpen} onClose={closeDialog} />
    </PageContainer>
  );
}
