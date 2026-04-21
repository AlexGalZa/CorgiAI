import { test, expect } from '@playwright/test'

test.describe('Smoke tests', () => {
  test('portal login page loads', async ({ page }) => {
    await page.goto('/login')
    await expect(page).toHaveTitle(/Corgi/)
    await expect(page.getByPlaceholder('you@company.com')).toBeVisible()
  })

  test('admin login page loads', async ({ page }) => {
    await page.goto('http://localhost:3001/login')
    await expect(page.getByText('Sign in')).toBeVisible()
  })

  test('API health check responds', async ({ request }) => {
    const resp = await request.get('http://localhost:8000/api/v1/health')
    expect(resp.ok()).toBeTruthy()
  })
})
