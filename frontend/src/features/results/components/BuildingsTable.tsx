import {
  Box,
  Button,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import type { BuildingRow } from '../schemas';
import { formatArea, formatConfidence } from '../format';

export interface BuildingsTableProps {
  buildings: BuildingRow[];
  selectedId?: string | null;
  onSelect: (buildingId: string) => void;
  count: number;
  page: number;
  hasPrev: boolean;
  hasNext: boolean;
  onPrev: () => void;
  onNext: () => void;
}

/** Paginated, keyboard-accessible table of detected buildings. */
export function BuildingsTable({
  buildings,
  selectedId = null,
  onSelect,
  count,
  page,
  hasPrev,
  hasNext,
  onPrev,
  onNext,
}: BuildingsTableProps): JSX.Element {
  return (
    <Box>
      <TableContainer>
        <Table size="small" aria-label="Detected buildings">
          <TableHead>
            <TableRow>
              <TableCell scope="col">#</TableCell>
              <TableCell scope="col" align="right">
                Roof area
              </TableCell>
              <TableCell scope="col" align="right">
                Confidence
              </TableCell>
              <TableCell scope="col" align="right">
                <span>Details</span>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {buildings.map((building) => (
              <TableRow key={building.id} selected={building.id === selectedId} hover>
                <TableCell>{building.index}</TableCell>
                <TableCell align="right">{formatArea(building.area_m2)}</TableCell>
                <TableCell align="right">{formatConfidence(building.confidence)}</TableCell>
                <TableCell align="right">
                  <Button
                    size="small"
                    onClick={() => onSelect(building.id)}
                    aria-label={`View details for building ${building.index}`}
                  >
                    View
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Stack
        direction="row"
        spacing={2}
        alignItems="center"
        justifyContent="space-between"
        sx={{ mt: 1.5 }}
      >
        <Typography variant="caption" color="text.secondary">
          {count} building{count === 1 ? '' : 's'} · page {page}
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button size="small" onClick={onPrev} disabled={!hasPrev}>
            Previous
          </Button>
          <Button size="small" onClick={onNext} disabled={!hasNext}>
            Next
          </Button>
        </Stack>
      </Stack>
    </Box>
  );
}
