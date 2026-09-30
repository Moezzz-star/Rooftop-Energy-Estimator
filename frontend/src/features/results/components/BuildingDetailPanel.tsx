import {
  Alert,
  Box,
  Divider,
  Drawer,
  IconButton,
  Stack,
  Typography,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import { LoadingState, ErrorState, EmptyState, DisclaimerBanner } from '@/components';
import { useBuildingDetail } from '../hooks';
import { MonthlyYieldChart } from './MonthlyYieldChart';
import {
  formatArea,
  formatCapacity,
  formatConfidence,
  formatDegrees,
  formatEnergy,
  formatInt,
} from '../format';

export interface BuildingDetailPanelProps {
  buildingId: string | null;
  onClose: () => void;
}

interface DetailRowProps {
  label: string;
  value: string;
}

function DetailRow({ label, value }: DetailRowProps): JSX.Element {
  return (
    <Stack direction="row" justifyContent="space-between" spacing={2}>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2">{value}</Typography>
    </Stack>
  );
}

/** Slide-in drawer with a building's roof geometry and solar estimate. */
export function BuildingDetailPanel({
  buildingId,
  onClose,
}: BuildingDetailPanelProps): JSX.Element {
  const detailQuery = useBuildingDetail(buildingId);
  const detail = detailQuery.data;
  const solar = detail?.solar_estimates[0] ?? null;

  return (
    <Drawer
      anchor="right"
      open={buildingId !== null}
      onClose={onClose}
      aria-label="Building detail"
      PaperProps={{ sx: { width: { xs: '100%', sm: 420 }, p: 3 } }}
    >
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h3" component="h2">
          Building detail
        </Typography>
        <IconButton onClick={onClose} aria-label="Close building detail">
          <CloseIcon />
        </IconButton>
      </Stack>

      {detailQuery.isPending && <LoadingState label="Loading building…" />}

      {detailQuery.isError && (
        <ErrorState
          message={detailQuery.error.message}
          onRetry={() => void detailQuery.refetch()}
        />
      )}

      {detail && (
        <Stack spacing={2.5} divider={<Divider flexItem />}>
          <Box>
            <Typography variant="h4" component="h3" gutterBottom>
              Overview
            </Typography>
            <Stack spacing={0.75}>
              <DetailRow label="Building #" value={formatInt(detail.index)} />
              <DetailRow label="Footprint area" value={formatArea(detail.area_m2)} />
              <DetailRow label="Detection confidence" value={formatConfidence(detail.confidence)} />
            </Stack>
          </Box>

          <Box>
            <Typography variant="h4" component="h3" gutterBottom>
              Roof
            </Typography>
            {detail.roof ? (
              <Stack spacing={0.75}>
                <DetailRow label="Tilt" value={formatDegrees(detail.roof.tilt_deg)} />
                <DetailRow label="Azimuth" value={formatDegrees(detail.roof.azimuth_deg)} />
                <DetailRow label="Usable area" value={formatArea(detail.roof.usable_area_m2)} />
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No roof geometry available.
              </Typography>
            )}
          </Box>

          <Box>
            <Typography variant="h4" component="h3" gutterBottom>
              Solar estimate
            </Typography>
            {solar ? (
              <Stack spacing={2}>
                <Stack spacing={0.75}>
                  <DetailRow label="Capacity" value={formatCapacity(solar.capacity_kwp)} />
                  <DetailRow label="Annual energy" value={formatEnergy(solar.annual_kwh)} />
                  <DetailRow
                    label="Specific yield"
                    value={`${formatInt(solar.specific_yield)} kWh/kWp`}
                  />
                </Stack>
                <MonthlyYieldChart monthlyKwh={solar.monthly_kwh} />
              </Stack>
            ) : (
              <EmptyState
                title="No solar estimate"
                description="This building has no solar estimate yet."
              />
            )}
          </Box>

          <DisclaimerBanner variant="banner" />

          {detail.warnings.length > 0 && (
            <Box>
              <Typography variant="h4" component="h3" gutterBottom>
                Data quality warnings
              </Typography>
              <Stack spacing={1} aria-label="Building data quality warnings">
                {detail.warnings.map((warning) => (
                  <Alert key={warning} severity="warning" variant="outlined">
                    {warning}
                  </Alert>
                ))}
              </Stack>
            </Box>
          )}
        </Stack>
      )}
    </Drawer>
  );
}
