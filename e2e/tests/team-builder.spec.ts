import { test, expect } from '@playwright/test';

test.describe('Team builder flow', () => {
  test('team builder page loads correctly', async ({ page }) => {
    await page.goto('/team-builder');

    // Check page title
    await expect(page.getByRole('heading', { name: 'Team Builder' })).toBeVisible();

    // Check team builder component exists
    await expect(page.getByTestId('team-builder')).toBeVisible();

    // Check budget tracker exists
    await expect(page.getByTestId('budget-remaining')).toBeVisible();
  });

  test('budget tracker shows correct initial value', async ({ page }) => {
    await page.goto('/team-builder');

    // Check initial budget
    const budgetElement = page.getByTestId('budget-remaining');
    await expect(budgetElement).toContainText('230');
  });

  test('team count shows initially zero', async ({ page }) => {
    await page.goto('/team-builder');

    // Check team count
    const teamCount = page.getByTestId('team-count');
    await expect(teamCount).toContainText('0 players');
  });

  test('available players section exists', async ({ page }) => {
    await page.goto('/team-builder');

    // Check available players section
    await expect(page.getByRole('heading', { name: 'Available Players' })).toBeVisible();
  });

  test('clear team button exists', async ({ page }) => {
    await page.goto('/team-builder');

    // Check clear button
    await expect(page.getByRole('button', { name: 'Clear Team' })).toBeVisible();
  });
});
