import { useMemo, useState } from 'react';
import { Box, Paper, Stack, Typography } from '@mui/material';
import { LoadingState, ErrorState, EmptyState } from '@/components';
import { RoofMap } from '@/features/map';
import { useAnalysis } from '@/features/analyses';
import { ExportButtons } from '@/features/exports';
import { geometryBBox, padBBox, type BBox } from '@/maps';
import { useResultsSummary, useBuildings, useMapFeatures } from '../hooks';
import type { BuildingRow } from '../schemas';
import { ZoneSummary } from './ZoneSummary';
import { BuildingsTable } from './BuildingsTable';
import { BuildingsFilters, type BuildingFilters } from './BuildingsFilters';
import { BuildingDetailPanel } from './BuildingDetailPanel';
import { DistributionChart } from './DistributionChart';
import { TransparencyPanel } from './TransparencyPanel';

export interface ResultsViewProps {
  analysisId: string;
}

const MAP_ZOOM = 16;

/** Collect defined values of a numeric metric from the loaded building rows. */
function collectMetric(rows: BuildingRow[], key: 'annual_kwh' | 'capacity_kwp'): number[] {
  const values: number[] = [];
  for (const row of rows) {
    const value = row[key];
    if (typeof value === 'number' && Number.isFinite(value)) values.push(value);
  }
  return values;
}

/** Full results screen: zone summary, roof map, distributions, table + detail. */
export function ResultsView({ analysisId }: ResultsViewProps): JSX.Element {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<BuildingFilters>({ order: '' });
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const analysisQuery = useAnalysis(analysisId);
  const summaryQuery = useResultsSummary(analysisId);

  const bounds: BBox | null = useMemo(() => {
    const area = analysisQuery.data?.areas[0]?.area;
    if (!area) return null;
    const box = geometryBBox(area);
    return box ? padBBox(box) : null;
  }, [analysisQuery.data]);

  const buildingsQuery = useBuildings(analysisId, {
    page,
    ...(filters.minArea !== undefined ? { min_area: filters.minArea } : {}),
    ...(filters.confidence !== undefined ? { confidence: filters.confidence } : {}),
    ...(filters.order !== '' ? { order: filters.order } : {}),
  });
  const featuresQuery = useMapFeatures(analysisId, bounds, MAP_ZOOM);

  const rows = useMemo(
    () => buildingsQuery.data?.results ?? [],
    [buildingsQuery.data],
  );
  const annualValues = useMemo(() => collectMetric(rows, 'annual_kwh'), [rows]);
  const capacityValues = useMemo(() => collectMetric(rows, 'capacity_kwp'), [rows]);

  const handleFiltersChange = (next: BuildingFilters): void => {
    setFilters(next);
    setPage(1);
  };

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h3" component="h2" gutterBottom>
          Zone summary
        </Typography>
        {summaryQuery.isPending && <LoadingState label="Loading summary…" />}
        {summaryQuery.isError && (
          <ErrorState
            message={summaryQuery.error.message}
            onRetry={() => void summaryQuery.refetch()}
          />
        )}
        {summaryQuery.isSuccess && <ZoneSummary summary={summaryQuery.data} />}
      </Box>

      <Box>
        <Typography variant="h3" component="h2" gutterBottom>
          Roof map
        </Typography>
        <Paper variant="outlined" sx={{ height: 420, overflow: 'hidden' }}>
          {featuresQuery.isError ? (
            <Box sx={{ p: 2 }}>
              <ErrorState
                message={featuresQuery.error.message}
                onRetry={() => void featuresQuery.refetch()}
              />
            </Box>
          ) : (
            <RoofMap
              features={featuresQuery.data ?? null}
              bounds={bounds}
              selectedId={selectedId}
              onSelectBuilding={setSelectedId}
            />
          )}
        </Paper>
      </Box>

      <Box>
        <Typography variant="h3" component="h2" gutterBottom>
          Distributions
        </Typography>
        <Box
          sx={{
            display: 'grid',
            gap: 3,
            gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' },
          }}
        >
          <DistributionChart
            title="Annual energy potential"
            values={annualValues}
            unit="kWh"
            emptyDescription="Per-building annual energy is not included in the buildings list for this analysis."
          />
          <DistributionChart
            title="Capacity"
            values={capacityValues}
            unit="kWp"
            color="#238636"
            emptyDescription="Per-building capacity is not included in the buildings list for this analysis."
          />
        </Box>
      </Box>

      <Box>
        <Typography variant="h3" component="h2" gutterBottom>
          Buildings
        </Typography>
        <BuildingsFilters value={filters} onChange={handleFiltersChange} />
        {buildingsQuery.isPending && <LoadingState label="Loading buildings…" />}
        {buildingsQuery.isError && (
          <ErrorState
            message={buildingsQuery.error.message}
            onRetry={() => void buildingsQuery.refetch()}
          />
        )}
        {buildingsQuery.isSuccess &&
          (buildingsQuery.data.results.length === 0 ? (
            <EmptyState
              title="No buildings match"
              description="No building footprints match the current filters."
            />
          ) : (
            <BuildingsTable
              buildings={buildingsQuery.data.results}
              selectedId={selectedId}
              onSelect={setSelectedId}
              count={buildingsQuery.data.count}
              page={page}
              hasPrev={buildingsQuery.data.previous !== null}
              hasNext={buildingsQuery.data.next !== null}
              onPrev={() => setPage((current) => Math.max(1, current - 1))}
              onNext={() => setPage((current) => current + 1)}
            />
          ))}
      </Box>

      <Box>
        <Typography variant="h3" component="h2" gutterBottom>
          Transparency
        </Typography>
        {summaryQuery.isSuccess && <TransparencyPanel summary={summaryQuery.data} />}
      </Box>

      <Box>
        <ExportButtons analysisId={analysisId} />
      </Box>

      <BuildingDetailPanel buildingId={selectedId} onClose={() => setSelectedId(null)} />
    </Stack>
  );
}
