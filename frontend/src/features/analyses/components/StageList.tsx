import { Box, LinearProgress, List, ListItem, ListItemText, Stack, Typography } from '@mui/material';
import { StatusChip } from '@/components';
import { formatStageLabel } from '../stageLabels';
import type { JobStage } from '../schemas';

export interface StageListProps {
  /** Stages exactly as returned by GET /analyses/{id}/job/ (drives the UI). */
  stages: JobStage[];
}

const DONE_STATUSES = new Set(['succeeded', 'skipped', 'failed']);

function formatDuration(ms: number | null): string | undefined {
  if (ms === null) return undefined;
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

/**
 * Renders the pipeline stages driven entirely by the polled job response. Each
 * stage label comes from `formatStageLabel` (humanize fallback for unknown
 * keys); progress reflects real per-stage statuses, never a fake percentage.
 */
export function StageList({ stages }: StageListProps): JSX.Element {
  const ordered = [...stages].sort((a, b) => a.sequence - b.sequence);
  const total = ordered.length;
  const done = ordered.filter((stage) => DONE_STATUSES.has(stage.status)).length;
  const percent = total === 0 ? 0 : Math.round((done / total) * 100);

  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <LinearProgress
          variant="determinate"
          value={percent}
          aria-label="Overall processing progress"
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
        />
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
          {done} of {total} stages complete ({percent}%)
        </Typography>
      </Box>
      <List aria-label="Pipeline stages">
        {ordered.map((stage) => {
          const duration = formatDuration(stage.duration_ms);
          const detailMessage =
            typeof stage.detail?.message === 'string' ? stage.detail.message : undefined;
          const secondary = [detailMessage, duration ? `Took ${duration}` : undefined]
            .filter(Boolean)
            .join(' · ');
          return (
            <ListItem
              key={stage.name}
              disableGutters
              secondaryAction={
                <Stack direction="row" spacing={1} alignItems="center">
                  <StatusChip status={stage.status} />
                </Stack>
              }
            >
              <ListItemText
                primary={formatStageLabel(stage.name)}
                secondary={secondary.length > 0 ? secondary : undefined}
              />
            </ListItem>
          );
        })}
      </List>
    </Box>
  );
}
