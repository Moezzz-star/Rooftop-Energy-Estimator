import { useState } from 'react';
import {
  Box,
  Button,
  CircularProgress,
  Stack,
  Typography,
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import { useCreateExport, useExport, useDownloadExport } from '../hooks';
import {
  exportKindSchema,
  isExportFailed,
  isExportReady,
  type ExportArtifact,
  type ExportKind,
} from '../schemas';

const KIND_LABELS: Record<ExportKind, string> = {
  csv: 'CSV',
  geojson: 'GeoJSON',
  pdf: 'PDF',
};

interface ExportKindButtonProps {
  analysisId: string;
  kind: ExportKind;
}

function ExportKindButton({ analysisId, kind }: ExportKindButtonProps): JSX.Element {
  const label = KIND_LABELS[kind];
  const [exportId, setExportId] = useState<string | null>(null);

  const createMutation = useCreateExport(analysisId);
  const pollQuery = useExport(exportId);
  const downloadMutation = useDownloadExport();

  const artifact: ExportArtifact | undefined = pollQuery.data ?? createMutation.data;
  const ready = artifact !== undefined && isExportReady(artifact);
  const failed =
    createMutation.isError ||
    pollQuery.isError ||
    (artifact !== undefined && isExportFailed(artifact));
  const building = !ready && !failed && (createMutation.isPending || exportId !== null);

  const handleGenerate = (): void => {
    setExportId(null);
    createMutation.mutate(kind, {
      onSuccess: (created) => setExportId(created.id),
    });
  };

  const handleDownload = (): void => {
    if (artifact) downloadMutation.mutate(artifact);
  };

  let status = '';
  if (building) status = `${label} export is being built…`;
  else if (failed) status = `${label} export failed.`;
  else if (ready) status = `${label} export is ready to download.`;

  return (
    <Box>
      {ready && artifact ? (
        <Button
          variant="contained"
          size="small"
          startIcon={<DownloadIcon />}
          onClick={handleDownload}
          disabled={downloadMutation.isPending}
          aria-label={`Download ${label} export`}
        >
          {downloadMutation.isPending ? 'Downloading…' : `Download ${label}`}
        </Button>
      ) : (
        <Button
          variant="outlined"
          size="small"
          onClick={handleGenerate}
          disabled={building}
          startIcon={building ? <CircularProgress size={16} aria-hidden /> : undefined}
          aria-label={
            failed ? `Retry ${label} export` : `Generate ${label} export`
          }
        >
          {building ? `Building ${label}…` : failed ? `Retry ${label}` : label}
        </Button>
      )}
      {status && (
        <Typography variant="caption" color={failed ? 'error' : 'text.secondary'} sx={{ display: 'block', mt: 0.5 }}>
          {status}
        </Typography>
      )}
      {downloadMutation.isError && (
        <Typography variant="caption" color="error" sx={{ display: 'block', mt: 0.5 }}>
          Download failed. Please try again.
        </Typography>
      )}
    </Box>
  );
}

export interface ExportButtonsProps {
  analysisId: string;
}

const EXPORT_KINDS: readonly ExportKind[] = exportKindSchema.options;

/**
 * CSV / GeoJSON / PDF export controls. Each button requests an async export,
 * polls until the artifact is ready, then offers an authenticated download.
 */
export function ExportButtons({ analysisId }: ExportButtonsProps): JSX.Element {
  return (
    <Box>
      <Typography variant="h4" component="h3" gutterBottom>
        Export results
      </Typography>
      <Stack
        direction="row"
        spacing={2}
        flexWrap="wrap"
        useFlexGap
        role="group"
        aria-label="Export results"
      >
        {EXPORT_KINDS.map((kind) => (
          <ExportKindButton key={kind} analysisId={analysisId} kind={kind} />
        ))}
      </Stack>
    </Box>
  );
}
