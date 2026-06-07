import { expect, test } from '@playwright/test';

type Mode = {
  button: string;
  submitButton: string;
  applicant: string;
};

const modes: Mode[] = [
  {
    button: 'Monolith',
    submitButton: 'Submit (monolith)',
    applicant: 'pw-mono',
  },
  {
    button: 'Microservices',
    submitButton: 'Submit (microservices)',
    applicant: 'pw-micro',
  },
  {
    button: 'Event Sourcing + CQRS',
    submitButton: 'Submit (event-sourcing)',
    applicant: 'pw-cqrs',
  },
];

test('submissions work across all architecture modes', async ({ page }) => {
  await page.goto('/');
  await expect(
    page.getByRole('heading', { name: 'Insurance Architecture Pattern Simulator' }),
  ).toBeVisible();

  const modeSelector = page.getByRole('tablist', { name: 'Architecture mode selector' });

  for (const mode of modes) {
    await modeSelector.getByRole('button', { name: mode.button, exact: true }).click();

    const applicant = `${mode.applicant}-${Date.now()}`;
    await page.getByLabel('Applicant name').fill(applicant);
    await page.getByRole('button', { name: mode.submitButton }).click();

    await expect(page.getByText(/Submission:\s*/)).toBeVisible();
    await expect(page.getByText('not started')).toHaveCount(0);

    await expect(page.getByRole('button', { name: 'Refresh Data' })).toBeVisible();
    await expect(page.locator('.event-card').first()).toBeVisible({ timeout: 30_000 });

    await page.getByRole('button', { name: 'Refresh Data' }).click();
    await expect(page.getByRole('button', { name: 'Refresh Data' })).toBeVisible();
  }
});
