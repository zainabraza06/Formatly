/**
 * Drive the real app in a browser: photograph every screen at every breakpoint
 * that matters, in both themes, and run an accessibility audit on each one.
 *
 * Screens are judged by looking at them. This is how they get looked at.
 *
 *   npm run shots                     # screenshots + audit into ./ui-shots
 *   SEED=/path/to/docx npm run shots  # upload some .docx first, for real rows
 *
 * It needs the app running: the API on 8000 and Vite on 5173.
 */
import { chromium } from 'playwright'
import { AxeBuilder } from '@axe-core/playwright'
import fs from 'node:fs'
import path from 'node:path'

const OUT = process.argv[2] || './ui-shots'
const APP = process.env.APP || 'http://localhost:5173'
const SEED = process.env.SEED || ''
const EMAIL = `ui${Date.now()}@check.test`

fs.mkdirSync(OUT, { recursive: true })

const SIZES = {
  desktop: { width: 1440, height: 900 },
  phone: { width: 375, height: 812 },
}

const audits = []

async function shoot(page, name, { full = false, audit = false } = {}) {
  await page.waitForTimeout(400)
  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: full })

  if (audit) {
    // WCAG 2.1 A and AA, which is what the design system claims to meet.
    const { violations } = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()
    audits.push({ screen: name, violations })
    const worst = violations.filter((v) => v.impact === 'critical' || v.impact === 'serious')
    console.log(`shot ${name} — ${violations.length} a11y issue(s), ${worst.length} serious+`)
    for (const v of violations) {
      console.log(`    [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length})`)
    }
    return
  }
  console.log('shot', name)
}

const browser = await chromium.launch()

/** A page in its own context: axe refuses to run against browser.newPage(). */
async function newPage(viewport) {
  const context = await browser.newContext({ viewport, deviceScaleFactor: 2 })
  return context.newPage()
}

// ── The public page, which nobody is signed in for ──────────────────────────
for (const [label, size] of Object.entries(SIZES)) {
  const page = await newPage(size)
  await page.goto(APP, { waitUntil: 'networkidle' })
  await shoot(page, `landing-${label}`, { full: label === 'desktop', audit: label === 'desktop' })

  if (label === 'desktop') {
    // Dark mode is half the product; it gets looked at too.
    await page.getByRole('button', { name: /switch to dark theme/i }).click()
    await page.waitForTimeout(500)
    await shoot(page, 'landing-dark', { full: true })
    await page.getByRole('button', { name: /switch to light theme/i }).click()
  }
  await page.close()
}

// ── Signed in ───────────────────────────────────────────────────────────────
const page = await newPage(SIZES.desktop)
page.on('console', (m) => m.type() === 'error' && console.log('CONSOLE ERROR:', m.text()))
page.on('pageerror', (e) => console.log('PAGE ERROR:', e.message))

await page.goto(`${APP}/login`, { waitUntil: 'networkidle' })
await shoot(page, 'login', { audit: true })

await page.getByRole('button', { name: /create one/i }).click()
await page.getByLabel('Name').fill('Zainab')
await page.getByLabel('Email').fill(EMAIL)
await page.getByLabel('Password').fill('password1')
await page.getByRole('button', { name: /create account/i }).click()
await page.waitForURL('**/app', { timeout: 20000 })
await page.waitForTimeout(800)
await shoot(page, 'documents-empty')

// Upload the seeded documents through the real UI, when there are any.
for (const file of (SEED && fs.existsSync(SEED) ? fs.readdirSync(SEED) : [])) {
  await page.goto(`${APP}/app`, { waitUntil: 'networkidle' })
  const input = page.locator('#library-upload')
  await input.setInputFiles(path.join(SEED, file))
  await page.waitForURL('**/app/editor**', { timeout: 40000 })
  await page.waitForTimeout(1500)
}

await page.goto(`${APP}/app`, { waitUntil: 'networkidle' })
await page.waitForTimeout(1200)
await shoot(page, 'documents-list', { audit: true })

// The grid, for comparison.
await page.getByRole('tab', { name: 'Grid' }).click()
await page.waitForTimeout(400)
await shoot(page, 'documents-grid')
await page.getByRole('tab', { name: 'List' }).click()

// The command palette.
await page.keyboard.press('Control+k')
await page.waitForTimeout(400)
await shoot(page, 'command-palette')
await page.keyboard.press('Escape')

// A row's action menu.
await page.locator('table button[aria-haspopup="menu"]').first().click()
await page.waitForTimeout(300)
await shoot(page, 'documents-menu')
await page.keyboard.press('Escape')

// ── The editor, with a real document open ───────────────────────────────────
await page.locator('table tbody tr').first().locator('button').first().click()
await page.waitForURL('**/app/editor**', { timeout: 30000 })
await page.waitForTimeout(3000)
await shoot(page, 'editor', { audit: true })

await page.getByRole('tab', { name: 'Structure' }).click()
await page.waitForTimeout(400)
await shoot(page, 'editor-structure')

await page.getByRole('tab', { name: 'History' }).click()
await page.waitForTimeout(400)
await shoot(page, 'editor-history')

await page.getByRole('button', { name: /^Export$/ }).click()
await page.waitForTimeout(4000)
await shoot(page, 'editor-export')
await page.keyboard.press('Escape')

// ── The generator ───────────────────────────────────────────────────────────
await page.goto(`${APP}/app/compose`, { waitUntil: 'networkidle' })
await page.waitForTimeout(600)
await shoot(page, 'compose-material', { audit: true })

await page.locator('#compose-material').fill(
  'Write a report on our Q3 customer churn for the leadership team.\n\n' +
  'Survey: 412 cancelling customers. Price 63%, missing features 21%, support 11%, other 5%.\n' +
  'Churn by month: July 4.2%, August 5.1%, September 6.8%.',
)
await page.getByRole('button', { name: /^Continue$/ }).click()
await page.waitForTimeout(500)
await shoot(page, 'compose-structure')

await page.getByRole('button', { name: /start from a typical outline/i }).click()
await page.waitForTimeout(300)
await shoot(page, 'compose-outline')

await page.getByRole('button', { name: /^Continue$/ }).click()
await page.waitForTimeout(500)
await shoot(page, 'compose-review')

// ── Settings ────────────────────────────────────────────────────────────────
await page.goto(`${APP}/app/settings`, { waitUntil: 'networkidle' })
await page.waitForTimeout(500)
await shoot(page, 'settings', { audit: true })

// ── Dark, and small ─────────────────────────────────────────────────────────
await page.goto(`${APP}/app`, { waitUntil: 'networkidle' })
await page.getByRole('button', { name: /switch to dark theme/i }).click()
await page.waitForTimeout(600)
await shoot(page, 'documents-dark')
await page.goto(`${APP}/app/editor`, { waitUntil: 'networkidle' })
await page.waitForTimeout(1500)
await shoot(page, 'editor-dark')
await page.getByRole('button', { name: /switch to light theme/i }).click()

await page.setViewportSize(SIZES.phone)
await page.goto(`${APP}/app`, { waitUntil: 'networkidle' })
await page.waitForTimeout(800)
await shoot(page, 'documents-phone')
await page.goto(`${APP}/app/editor`, { waitUntil: 'networkidle' })
await page.waitForTimeout(2000)
await shoot(page, 'editor-phone')

await browser.close()
console.log('\nAccount used:', EMAIL)
