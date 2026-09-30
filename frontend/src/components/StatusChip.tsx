import { Chip, type ChipProps } from '@mui/material';
import type { AnalysisStatus, JobStatus, JobStageStatus } from '@/schemas';

export type StatusValue = AnalysisStatus | JobStatus | JobStageStatus;

type ChipColor = NonNullable<ChipProps['color']>;

const STATUS_CONFIG: Record<string, { label: string; color: ChipColor }> = {
  // Analysis / job lifecycle
  draft: { label: 'Draft', color: 'default' },
  queued: { label: 'Queued', color: 'info' },
  running: { label: 'Running', color: 'warning' },
  completed: { label: 'Completed', color: 'success' },
  failed: { label: 'Failed', color: 'error' },
  cancelled: { label: 'Cancelled', color: 'default' },
  // Job stage
  pending: { label: 'Pending', color: 'default' },
  succeeded: { label: 'Succeeded', color: 'success' },
  skipped: { label: 'Skipped', color: 'default' },
};

export interface StatusChipProps {
  status: StatusValue;
  size?: ChipProps['size'];
}

/**
 * Renders a colored chip for any analysis/job/stage status. Color is paired
 * with an explicit text label so meaning is never conveyed by color alone.
 */
export function StatusChip({ status, size = 'small' }: StatusChipProps): JSX.Element {
  const config = STATUS_CONFIG[status] ?? { label: status, color: 'default' as ChipColor };
  return (
    <Chip
      label={config.label}
      color={config.color}
      size={size}
      variant={config.color === 'default' ? 'outlined' : 'filled'}
      aria-label={`Status: ${config.label}`}
    />
  );
}
