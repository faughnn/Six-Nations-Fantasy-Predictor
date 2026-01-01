import { test, expect } from '@playwright/test';

test.describe('Full user workflow', () => {
  test('complete navigation flow', async ({ page }) => {
    // 1. Start at dashboard
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

    // 2. Navigate to players
    await page.getByRole('link', { name: 'Players' }).click();
    await expect(page.getByRole('heading', { name: 'Players' })).toBeVisible();

    // 3. Navigate to compare
    await page.getByRole('link', { name: 'Compare' }).click();
    await expect(page.getByRole('heading', { name: 'Compare Players' })).toBeVisible();

    // 4. Navigate to optimiser
    await page.getByRole('link', { name: 'Optimiser' }).click();
    await expect(page.getByRole('heading', { name: 'Team Optimiser' })).toBeVisible();

    // 5. Navigate to team builder
    await page.getByRole('link', { name: 'Team Builder' }).click();
    await expect(page.getByRole('heading', { name: 'Team Builder' })).toBeVisible();

    // 6. Navigate to admin
    await page.getByRole('link', { name: 'Admin' }).click();
    await expect(page.getByRole('heading', { name: 'Admin' })).toBeVisible();
  });

  test('dashboard shows key metrics', async ({ page }) => {
    await page.goto('/');

    // Check dashboard has key cards
    await expect(page.getByText('Available Players')).toBeVisible();
    await expect(page.getByText('Budget')).toBeVisible();
  });

  test('compare page has filters', async ({ page }) => {
    await page.goto('/compare');

    // Check comparison filters exist
    await expect(page.getByLabel('Round')).toBeVisible();
    await expect(page.getByLabel('Position')).toBeVisible();
  });

  test('admin page has scraping controls', async ({ page }) => {
    await page.goto('/admin');

    // Check scraping section exists
    await expect(page.getByRole('heading', { name: 'Data Scraping' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Scrape Odds' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Scrape Prices' })).toBeVisible();
  });

  test('pages are responsive', async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // Navigation should still work
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

    // Test tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  });
});
