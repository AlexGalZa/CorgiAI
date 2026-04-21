import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  retries: 0,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },
  webServer: [
    {
      command: 'cd ../portal && pnpm run dev',
      port: 3000,
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: 'cd ../api && python manage.py runserver',
      port: 8000,
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
})
