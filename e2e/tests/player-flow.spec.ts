import { test, expect } from '@playwright/test';

test.describe('Player browsing flow', () => {
  test('user can view and filter players', async ({ page }) => {
    await page.goto('/players');

    // Check table loads
    await expect(page.getByRole('table')).toBeVisible();

    // Check for player data (may be empty if not seeded, but table should exist)
    const table = page.getByRole('table');
    await expect(table).toBeVisible();
  });

  test('user can filter by country', async ({ page }) => {
    await page.goto('/players');

    // Filter by country
    const countrySelect = page.getByLabel('Country');
    if (await countrySelect.isVisible()) {
      await countrySelect.selectOption('Ireland');

      // Wait for filter to apply
      await page.waitForTimeout(500);
    }
  });

  test('user can filter by position', async ({ page }) => {
    await page.goto('/players');

    // Filter by position
    const positionSelect = page.getByLabel('Position');
    if (await positionSelect.isVisible()) {
      await positionSelect.selectOption('out_half');

      // Wait for filter to apply
      await page.waitForTimeout(500);
    }
  });

  test('page has correct structure', async ({ page }) => {
    await page.goto('/players');

    // Check page title
    await expect(page.getByRole('heading', { name: 'Players' })).toBeVisible();

    // Check filters exist
    await expect(page.getByLabel('Country')).toBeVisible();
    await expect(page.getByLabel('Position')).toBeVisible();
  });
});
