import {
  Box,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Slider,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
  type SelectChangeEvent,
} from '@mui/material';
import CropFreeIcon from '@mui/icons-material/CropFree';
import { MapLegend } from './MapLegend';
import {
  type FillMode,
  type SolarMetricConfig,
  type SolarMetricKey,
} from '../mapStyle';

export interface MapControlsProps {
  fillMode: FillMode;
  onFillModeChange: (mode: FillMode) => void;
  /** Solar metrics actually present in the data (empty ⇒ thematic disabled). */
  availableMetrics: SolarMetricConfig[];
  metric: SolarMetricKey;
  onMetricChange: (metric: SolarMetricKey) => void;
  /** Domain of the active metric for the legend; null hides the legend. */
  domain: [number, number] | null;
  opacity: number;
  onOpacityChange: (opacity: number) => void;
  onFitBounds: () => void;
  canFit: boolean;
}

const IMAGERY_UNAVAILABLE =
  'Aerial imagery is unavailable in the offline sample — no tiles are served.';
const MASK_UNAVAILABLE =
  'The segmentation mask overlay is unavailable in the offline sample.';

/**
 * Presentational overlay panel for the roof map: layer toggles, an opacity
 * control, metric selector, legend and a fit-to-bounds button. Holds no map
 * state itself — RoofMap owns the state and applies it to MapLibre.
 */
export function MapControls({
  fillMode,
  onFillModeChange,
  availableMetrics,
  metric,
  onMetricChange,
  domain,
  opacity,
  onOpacityChange,
  onFitBounds,
  canFit,
}: MapControlsProps): JSX.Element {
  const thematicAvailable = availableMetrics.length > 0;
  const activeMetricConfig = availableMetrics.find((item) => item.key === metric) ?? null;

  const handleFillMode = (
    _event: React.MouseEvent<HTMLElement>,
    next: FillMode | null,
  ): void => {
    if (next !== null) onFillModeChange(next);
  };

  const handleMetric = (event: SelectChangeEvent): void => {
    onMetricChange(event.target.value as SolarMetricKey);
  };

  return (
    <Paper
      elevation={3}
      aria-label="Map layers and display controls"
      sx={{
        position: 'absolute',
        top: 8,
        left: 8,
        zIndex: 1,
        p: 1.5,
        maxWidth: 232,
        display: 'flex',
        flexDirection: 'column',
        gap: 1.25,
      }}
    >
      <Box>
        <Typography variant="caption" color="text.secondary" component="p" sx={{ mb: 0.5 }}>
          Roof colouring
        </Typography>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={fillMode}
          onChange={handleFillMode}
          aria-label="Roof fill mode"
          fullWidth
        >
          <ToggleButton value="polygons" aria-label="Solid polygons">
            Polygons
          </ToggleButton>
          <Tooltip
            title={
              thematicAvailable
                ? ''
                : 'No solar metric is available on these roof polygons.'
            }
          >
            <span>
              <ToggleButton
                value="thematic"
                aria-label="Solar thematic"
                disabled={!thematicAvailable}
              >
                Solar
              </ToggleButton>
            </span>
          </Tooltip>
        </ToggleButtonGroup>
      </Box>

      {fillMode === 'thematic' && thematicAvailable && (
        <FormControl size="small" fullWidth>
          <InputLabel id="map-metric-label">Metric</InputLabel>
          <Select
            labelId="map-metric-label"
            label="Metric"
            value={metric}
            onChange={handleMetric}
          >
            {availableMetrics.map((item) => (
              <MenuItem key={item.key} value={item.key}>
                {item.label} ({item.unit})
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}

      {fillMode === 'thematic' && activeMetricConfig && domain && (
        <MapLegend metric={activeMetricConfig} domain={domain} />
      )}

      <Box>
        <Typography
          variant="caption"
          color="text.secondary"
          component="label"
          id="map-opacity-label"
        >
          Roof opacity
        </Typography>
        <Slider
          size="small"
          value={Math.round(opacity * 100)}
          onChange={(_event, value) => onOpacityChange((Array.isArray(value) ? value[0]! : value) / 100)}
          min={10}
          max={100}
          step={5}
          aria-labelledby="map-opacity-label"
          valueLabelDisplay="auto"
          valueLabelFormat={(value) => `${value}%`}
        />
      </Box>

      <Divider flexItem />

      <Box>
        <Typography variant="caption" color="text.secondary" component="p" sx={{ mb: 0.5 }}>
          Base layers
        </Typography>
        <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
          <ToggleButton size="small" value="base" selected disabled aria-label="Base map (always on)">
            Base
          </ToggleButton>
          <Tooltip title={IMAGERY_UNAVAILABLE}>
            <span>
              <ToggleButton size="small" value="imagery" disabled aria-label="Aerial imagery (unavailable)">
                Imagery
              </ToggleButton>
            </span>
          </Tooltip>
          <Tooltip title={MASK_UNAVAILABLE}>
            <span>
              <ToggleButton size="small" value="mask" disabled aria-label="Segmentation mask (unavailable)">
                Mask
              </ToggleButton>
            </span>
          </Tooltip>
        </Stack>
      </Box>

      <ToggleButton
        size="small"
        value="fit"
        disabled={!canFit}
        onClick={onFitBounds}
        aria-label="Fit map to analysis area"
      >
        <CropFreeIcon fontSize="small" sx={{ mr: 0.5 }} />
        Fit to bounds
      </ToggleButton>
    </Paper>
  );
}
