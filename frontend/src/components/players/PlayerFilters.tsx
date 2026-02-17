import type { Country, Position } from '../../types';
import { getPositionLabel } from '../../utils';

interface Filters {
  country?: Country;
  position?: Position;
  minPrice?: number;
  maxPrice?: number;
  isAvailable?: boolean;
}

interface PlayerFiltersProps {
  filters: Filters;
  onChange: (filters: Filters) => void;
}

const COUNTRIES: Country[] = ['Ireland', 'England', 'France', 'Wales', 'Scotland', 'Italy'];
const POSITIONS: Position[] = [
  'prop',
  'hooker',
  'second_row',
  'back_row',
  'scrum_half',
  'out_half',
  'centre',
  'back_3',
];

export function PlayerFilters({ filters, onChange }: PlayerFiltersProps) {
  return (
    <div className="card mb-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 sm:gap-4">
        <div>
          <label htmlFor="country-filter" className="label">
            Country
          </label>
          <select
            id="country-filter"
            className="input"
            value={filters.country || ''}
            onChange={(e) =>
              onChange({ ...filters, country: e.target.value as Country || undefined })
            }
          >
            <option value="">All Countries</option>
            {COUNTRIES.map((country) => (
              <option key={country} value={country}>
                {country}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="position-filter" className="label">
            Position
          </label>
          <select
            id="position-filter"
            className="input"
            value={filters.position || ''}
            onChange={(e) =>
              onChange({ ...filters, position: e.target.value as Position || undefined })
            }
          >
            <option value="">All Positions</option>
            {POSITIONS.map((pos) => (
              <option key={pos} value={pos}>
                {getPositionLabel(pos)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="min-price" className="label">
            Min Price
          </label>
          <input
            id="min-price"
            type="number"
            className="input"
            placeholder="0"
            value={filters.minPrice || ''}
            onChange={(e) =>
              onChange({
                ...filters,
                minPrice: e.target.value ? parseFloat(e.target.value) : undefined,
              })
            }
          />
        </div>

        <div>
          <label htmlFor="max-price" className="label">
            Max Price
          </label>
          <input
            id="max-price"
            type="number"
            className="input"
            placeholder="30"
            value={filters.maxPrice || ''}
            onChange={(e) =>
              onChange({
                ...filters,
                maxPrice: e.target.value ? parseFloat(e.target.value) : undefined,
              })
            }
          />
        </div>

        <div>
          <label htmlFor="available-filter" className="label">
            Availability
          </label>
          <select
            id="available-filter"
            className="input"
            value={filters.isAvailable === undefined ? '' : filters.isAvailable.toString()}
            onChange={(e) =>
              onChange({
                ...filters,
                isAvailable:
                  e.target.value === '' ? undefined : e.target.value === 'true',
              })
            }
          >
            <option value="">All</option>
            <option value="true">Available</option>
            <option value="false">Not Available</option>
          </select>
        </div>
      </div>
    </div>
  );
}
