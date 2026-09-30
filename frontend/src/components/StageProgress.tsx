import { Box, LinearProgress, List, ListItem, ListItemText, Typography } from '@mui/material';
import type { JobStage } from '@/schemas';
import { stageLabel } from '@/schemas';
import { StatusChip } from './StatusChip';

export interface StageProgressProps {
  stages: JobStage[];
  /** Optional heading rendered above the progress bar. */
  title?: string;
}

const DONE_STATUSES = new Set(['succeeded', 'skipped', 'failed']);

/**
 * Presentational progress view for a processing job's stages. The wizard /
 * processing engineer feeds it the `stages[]` from `/analyses/{id}/job/`
 * (polled) — this component only renders; it does no data fetching.
 *
 * Extend freely (per-stage timings, expand/collapse) without changing the
 * public `stages` prop contract.
 */
export function StageProgress({ stages, title }: StageProgressProps): JSX.Element {
  const total = stages.length;
  const done = stages.filter((stage) => DONE_STATUSES.has(stage.status)).length;
  const percent = total === 0 ? 0 : Math.round((done / total) * 100);
  const ordered = [...stages].sort((a, b) => a.sequence - b.sequence);

  return (
    <Box>
      {title && (
        <Typography variant="h4" component="h2" gutterBottom>
          {title}
        </Typography>
      )}
      <Box sx={{ mb: 2 }}>
        <LinearProgress
          variant="determinate"
          value={percent}
          aria-label="Processing progress"
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
        />
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
          {done} of {total} stages complete ({percent}%)
        </Typography>
      </Box>
      <List dense aria-label="Pipeline stages">
        {ordered.map((stage) => (
          <ListItem
            key={stage.name}
            secondaryAction={<StatusChip status={stage.status} />}
            disableGutters
          >
            <ListItemText
              primary={stageLabel(stage.name)}
              secondary={
                typeof stage.detail?.message === 'string' ? stage.detail.message : undefined
              }
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
}
