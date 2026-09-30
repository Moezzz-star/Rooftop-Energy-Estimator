import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/renderWithProviders';
import { BuildingsFilters, type BuildingFilters } from './BuildingsFilters';

describe('BuildingsFilters', () => {
  it('emits min_area, confidence and order changes wired to the server params', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const value: BuildingFilters = { order: '' };
    renderWithProviders(<BuildingsFilters value={value} onChange={onChange} />, {
      withAuth: false,
    });

    await user.type(
      screen.getByLabelText('Minimum roof area in square metres'),
      '5',
    );
    expect(onChange).toHaveBeenLastCalledWith({ order: '', minArea: 5 });

    const combobox = screen.getByRole('combobox', { name: /sort by area/i });
    await user.click(combobox);
    await user.click(screen.getByRole('option', { name: /area \(descending\)/i }));
    expect(onChange).toHaveBeenLastCalledWith({ order: '-area_m2' });
  });

  it('disables Reset until a filter is active', () => {
    const onChange = vi.fn();
    renderWithProviders(
      <BuildingsFilters value={{ order: 'area_m2' }} onChange={onChange} />,
      { withAuth: false },
    );
    expect(screen.getByRole('button', { name: /reset/i })).toBeEnabled();
  });
});
