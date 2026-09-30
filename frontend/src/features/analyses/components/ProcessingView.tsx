import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, Box, Button, Paper, Stack, Typography } from '@mui/material';
import { LoadingState, ErrorState, StatusChip } from '@/components';
import { buildPath } from '@/routes/paths';
import { useJobPolling, useCancelJob } from '../hooks';
import { jobErrorMessage } from '../schemas';
import { StageList } from './StageList';

export interface ProcessingViewProps {
  analysisId: string;
}

const ACTIVE_STATUSES = new Set(['queued', 'running']);

/**
 * Live processing view. Polls the real job every 1.5s, renders stages from the
 * polled response, and reacts to terminal states (auto-navigate on success,
 * error + retry on failure, cancel while active).
 */
export function ProcessingView({ analysisId }: ProcessingViewProps): JSX.Element {
  const navigate = useNavigate();
  const jobQuery = useJobPolling(analysisId);
  const cancel = useCancelJob(analysisId);

  const job = jobQuery.data;
  const status = job?.status;
  const resultsPath = buildPath.analysisResults(analysisId);

  useEffect(() => {
    if (status !== 'succeeded') return undefined;
    const timer = window.setTimeout(() => navigate(resultsPath), 1200);
    return () => window.clearTimeout(timer);
  }, [status, navigate, resultsPath]);

  if (jobQuery.isPending) {
    return <LoadingState label="Loading job status…" />;
  }

  if (jobQuery.isError) {
    return (
      <ErrorState
        title="Could not load job status"
        message={jobQuery.error.message}
        onRetry={() => void jobQuery.refetch()}
      />
    );
  }

  if (!job) {
    return <ErrorState title="No job found" message="This analysis has no processing job yet." />;
  }

  const isActive = ACTIVE_STATUSES.has(job.status);
  const failureDetail = jobErrorMessage(job.error);

  return (
    <Stack spacing={3}>
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={2}
          justifyContent="space-between"
          alignItems={{ xs: 'flex-start', sm: 'center' }}
          sx={{ mb: 2 }}
        >
          <Box>
            <Typography variant="h4" component="h2">
              Processing analysis
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Progress reflects the real pipeline stages as they complete.
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2" color="text.secondary">
              Overall status:
            </Typography>
            <StatusChip status={job.status} />
          </Stack>
        </Stack>

        {status === 'succeeded' && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Processing complete. Redirecting to results…
          </Alert>
        )}
        {status === 'failed' && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Processing failed{failureDetail ? `: ${failureDetail}` : '.'}
          </Alert>
        )}
        {status === 'cancelled' && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            This job was cancelled.
          </Alert>
        )}

        <StageList stages={job.stages} />
      </Paper>

      <Stack direction="row" spacing={1.5} flexWrap="wrap">
        {status === 'succeeded' && (
          <Button variant="contained" onClick={() => navigate(resultsPath)}>
            View results
          </Button>
        )}
        {status === 'failed' && (
          <>
            <Button variant="contained" onClick={() => navigate('/dashboard')}>
              Back to dashboard
            </Button>
            <Button variant="outlined" onClick={() => void jobQuery.refetch()}>
              Refresh status
            </Button>
          </>
        )}
        {isActive && (
          <Button
            variant="outlined"
            color="error"
            disabled={cancel.isPending || job.cancel_requested === true}
            onClick={() => cancel.mutate()}
          >
            {cancel.isPending ? 'Cancelling…' : 'Cancel processing'}
          </Button>
        )}
      </Stack>

      {cancel.isError && <Alert severity="error">{cancel.error.message}</Alert>}
    </Stack>
  );
}
