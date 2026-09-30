import { Link as RouterLink } from 'react-router-dom';
import { Box, Button, Card, CardActions, CardContent, Chip, Typography } from '@mui/material';
import type { Project } from '@/schemas';
import { buildPath } from '@/routes/paths';

export interface ProjectListProps {
  projects: Project[];
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/** Presentational grid of project cards. Data fetching lives in feature hooks. */
export function ProjectList({ projects }: ProjectListProps): JSX.Element {
  return (
    <Box
      component="ul"
      sx={{
        listStyle: 'none',
        p: 0,
        m: 0,
        display: 'grid',
        gap: 2,
        gridTemplateColumns: {
          xs: '1fr',
          sm: 'repeat(2, 1fr)',
          md: 'repeat(3, 1fr)',
        },
      }}
    >
      {projects.map((project) => (
        <Box component="li" key={project.id} sx={{ display: 'flex' }}>
          <Card variant="outlined" sx={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
            <CardContent sx={{ flexGrow: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
                <Typography variant="h4" component="h3" noWrap title={project.name}>
                  {project.name}
                </Typography>
                {project.is_archived && <Chip label="Archived" size="small" variant="outlined" />}
              </Box>
              {project.description && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  {project.description}
                </Typography>
              )}
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1.5, display: 'block' }}>
                Created {formatDate(project.created_at)}
              </Typography>
            </CardContent>
            <CardActions>
              <Button
                component={RouterLink}
                to={buildPath.projectDetail(project.id)}
                size="small"
              >
                Open project
              </Button>
            </CardActions>
          </Card>
        </Box>
      ))}
    </Box>
  );
}
