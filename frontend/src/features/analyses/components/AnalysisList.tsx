import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Stack,
  Typography,
} from '@mui/material';
import { StatusChip } from '@/components';
import { buildPath } from '@/routes/paths';
import type { Analysis } from '@/schemas';

export interface AnalysisListProps {
  analyses: Analysis[];
}

function destinationFor(analysis: Analysis): string {
  return analysis.status === 'completed'
    ? buildPath.analysisResults(analysis.id)
    : buildPath.analysisProcessing(analysis.id);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/** Presentational list of a project's analyses; each card links by status. */
export function AnalysisList({ analyses }: AnalysisListProps): JSX.Element {
  return (
    <Box component="ul" sx={{ listStyle: 'none', p: 0, m: 0, display: 'grid', gap: 2 }}>
      {analyses.map((analysis) => (
        <Box component="li" key={analysis.id}>
          <Card variant="outlined">
            <CardActionArea component={RouterLink} to={destinationFor(analysis)}>
              <CardContent>
                <Stack
                  direction="row"
                  justifyContent="space-between"
                  alignItems="center"
                  spacing={2}
                >
                  <Box>
                    <Typography variant="h4" component="h3" title={analysis.name}>
                      {analysis.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Created {formatDate(analysis.created_at)}
                    </Typography>
                  </Box>
                  <StatusChip status={analysis.status} />
                </Stack>
              </CardContent>
            </CardActionArea>
          </Card>
        </Box>
      ))}
    </Box>
  );
}
