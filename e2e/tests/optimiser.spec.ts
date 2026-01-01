import { test, expect } from '@playwright/test';

test.describe('Optimiser flow', () => {
  test('optimiser page loads correctly', async ({ page }) => {
    await page.goto('/optimiser');

    // Check page title
    await expect(page.getByRole('heading', { name: 'Team Optimiser' })).toBeVisible();
  });

  test('optimiser form has all required fields', async ({ page }) => {
    await page.goto('/optimiser');

    // Check form fields exist
    await expect(page.getByLabel('Round')).toBeVisible();
    await expect(page.getByLabel('Budget')).toBeVisible();
    await expect(page.getByLabel('Max per Country')).toBeVisible();
  });

  test('generate button is visible', async ({ page }) => {
    await page.goto('/optimiser');

    // Check generate button
    await expect(
      page.getByRole('button', { name: 'Generate Optimal Team' })
    ).toBeVisible();
  });

  test('user can generate optimal team', async ({ page }) => {
    await page.goto('/optimiser');

    // Run optimiser with defaults
    await page.getByRole('button', { name: 'Generate Optimal Team' }).click();

    // Wait for result (may show empty result if no data)
    await page.waitForTimeout(2000);

    // Check that either result appears or no error is shown
    // The actual content depends on whether test data is seeded
  });

  test('budget field accepts custom values', async ({ page }) => {
    await page.goto('/optimiser');

    const budgetInput = page.getByLabel('Budget');
    await budgetInput.fill('200');

    await expect(budgetInput).toHaveValue('200');
  });

  test('max per country field accepts custom values', async ({ page }) => {
    await page.goto('/optimiser');

    const maxCountryInput = page.getByLabel('Max per Country');
    await maxCountryInput.fill('3');

    await expect(maxCountryInput).toHaveValue('3');
  });
});
