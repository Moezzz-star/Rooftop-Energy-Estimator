import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  type SelectChangeEvent,
} from '@mui/material';

export type BuildingsOrder = '' | 'area_m2' | '-area_m2';

export interface BuildingFilters {
  /** Minimum footprint area in m² (undefined = no filter). */
  minArea?: number | undefined;
  /** Minimum detection confidence 0..1 (undefined = no filter). */
  confidence?: number | undefined;
  /** Server ordering key (empty = default order). */
  order: BuildingsOrder;
}

export interface BuildingsFiltersProps {
  value: BuildingFilters;
  onChange: (next: BuildingFilters) => void;
}

/** Parse a numeric text input into a number or undefined (empty/invalid). */
function toNumberOrUndefined(raw: string): number | undefined {
  if (raw.trim() === '') return undefined;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : undefined;
}

/**
 * Filter/sort controls for the buildings table, wired to the server-side
 * `min_area`, `confidence` and `order` query params (code-architecture §4 #17).
 */
export function BuildingsFilters({ value, onChange }: BuildingsFiltersProps): JSX.Element {
  const handleMinArea = (event: React.ChangeEvent<HTMLInputElement>): void => {
    onChange({ ...value, minArea: toNumberOrUndefined(event.target.value) });
  };

  const handleConfidence = (event: React.ChangeEvent<HTMLInputElement>): void => {
    onChange({ ...value, confidence: toNumberOrUndefined(event.target.value) });
  };

  const handleOrder = (event: SelectChangeEvent): void => {
    onChange({ ...value, order: event.target.value as BuildingsOrder });
  };

  const handleReset = (): void => {
    onChange({ order: '' });
  };

  const hasFilters =
    value.minArea !== undefined || value.confidence !== undefined || value.order !== '';

  return (
    <Box
      component="form"
      aria-label="Filter and sort buildings"
      onSubmit={(event) => event.preventDefault()}
      sx={{ mb: 2 }}
    >
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        alignItems={{ xs: 'stretch', sm: 'flex-end' }}
      >
        <TextField
          size="small"
          type="number"
          label="Min roof area (m²)"
          value={value.minArea ?? ''}
          onChange={handleMinArea}
          inputProps={{ min: 0, step: 10, 'aria-label': 'Minimum roof area in square metres' }}
        />
        <TextField
          size="small"
          type="number"
          label="Min confidence (0–1)"
          value={value.confidence ?? ''}
          onChange={handleConfidence}
          inputProps={{
            min: 0,
            max: 1,
            step: 0.05,
            'aria-label': 'Minimum detection confidence between 0 and 1',
          }}
        />
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel id="buildings-order-label">Sort by area</InputLabel>
          <Select
            labelId="buildings-order-label"
            label="Sort by area"
            value={value.order}
            onChange={handleOrder}
          >
            <MenuItem value="">Default order</MenuItem>
            <MenuItem value="area_m2">Area (ascending)</MenuItem>
            <MenuItem value="-area_m2">Area (descending)</MenuItem>
          </Select>
        </FormControl>
        <Button size="small" onClick={handleReset} disabled={!hasFilters}>
          Reset
        </Button>
      </Stack>
    </Box>
  );
}
