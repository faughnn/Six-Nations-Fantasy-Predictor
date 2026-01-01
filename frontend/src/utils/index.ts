import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(price: number | null): string {
  if (price === null) return '-';
  return `${price.toFixed(1)}`;
}

export function formatPoints(points: number | null): string {
  if (points === null) return '-';
  return points.toFixed(1);
}

export function getPositionLabel(position: string): string {
  const labels: Record<string, string> = {
    prop: 'Prop',
    hooker: 'Hooker',
    second_row: 'Lock',
    back_row: 'Back Row',
    scrum_half: 'Scrum Half',
    out_half: 'Fly Half',
    centre: 'Centre',
    back_3: 'Back 3',
  };
  return labels[position] || position;
}

export function getCountryFlag(country: string): string {
  const flags: Record<string, string> = {
    Ireland: '🇮🇪',
    England: '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
    France: '🇫🇷',
    Wales: '🏴󠁧󠁢󠁷󠁬󠁳󠁿',
    Scotland: '🏴󠁧󠁢󠁳󠁣󠁴󠁿',
    Italy: '🇮🇹',
  };
  return flags[country] || '';
}
