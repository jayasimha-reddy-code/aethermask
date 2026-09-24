import { chromium } from 'playwright';
import fs from 'node:fs';

const BASE = 'http://127.0.0.1:8000';
const SHOTS = '/home/user/.probe/shots';
fs.mkdirSync(SHOTS, { recursive: true });

const results = [];
const ok = (name, cond, extra = '') => {
  results.push({ name, pass: !!cond, extra });
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? `  [${extra}]` : ''}`);
};

const browser = await chromium.launch({ args: ['--no-sandbox'] });
const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
const page = await ctx.newPage();

// --- independent egress observation -------------------------------------
const external = [];
const allReqs = [];
page.on('request', (r) => {
  const u = r.url();
  allReqs.push(u);
  if (!u.startsWith(BASE) && !u.startsWith('data:') && !u.startsWith('blob:')) {
    external.push(u);
  }
});
const consoleErrors = [];
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
page.on('pageerror', (e) => consoleErrors.push(`pageerror: ${e.message}`));

/* ===================== STAGE 1 : INGEST ===================== */
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(900);

ok('app renders header', await page.locator('text=AetherMask').first().isVisible());
ok('air-gap badge shows 0 external calls',
   await page.locator('text=/Air-gapped.*0 external calls/').isVisible());
const railStages = await page.locator('nav[aria-label="Pipeline stage"] li').count();
ok('stage rail exposes the full pipeline (ingest→profile→transform→vault→restore→audit)',
   railStages === 6, `stages=${railStages}`);

const lexVisible = await page.locator('text=Local lexicon capacity').isVisible();
ok('lexicon capacity panel visible', lexVisible);
if (lexVisible) {
  const panel = page.locator('section', { hasText: 'Local lexicon capacity' }).last();
  const surro = (await panel.innerText()).replace(/\n/g, ' ');
  // Parse the rendered number rather than pattern-matching a fixed magnitude, so
  // the assertion keeps working as the lexicon grows.
  const shown = /SURROGATES\s+([\d,]+)/i.exec(surro);
  const surrogates = shown ? Number(shown[1].replace(/,/g, '')) : 0;
  ok('lexicon panel reports the full surrogate capacity',
     surrogates >= 100000, `surrogates=${surrogates}`);
}

await page.setInputFiles('input[type=file]', '/home/user/aethermask/samples/classified_missions.csv');
await page.waitForTimeout(500);
ok('file chip shows filename', await page.locator('text=classified_missions.csv').first().isVisible());
await page.screenshot({ path: `${SHOTS}/v2-1-ingest.png`, fullPage: true });

/* ===================== STAGE 2 : PROFILE ===================== */
await page.click('button:has-text("Analyse sensitivity")');
await page.waitForSelector('text=/risk score/', { timeout: 60000 });
await page.waitForTimeout(700);
const riskTxt = await page.locator('text=/risk score/').first().innerText();
ok('risk grade rendered', /risk score/.test(riskTxt), riskTxt.replace(/\n/g, ' '));
ok('finding distribution rendered', await page.locator('text=Sensitivity findings by rule').isVisible());

// expand a column row to prove the accordion animates open
const firstCol = page.locator('button[aria-expanded]').first();
await firstCol.click();
await page.waitForTimeout(400);
ok('column detail expands', (await firstCol.getAttribute('aria-expanded')) === 'true');
await page.screenshot({ path: `${SHOTS}/v2-2-profile.png`, fullPage: true });

/* ===================== STAGE 3 : TRANSFORM ===================== */
await page.click('button:has-text("Configure transform")');
await page.waitForSelector('text=Cover domain profile', { timeout: 20000 });
await page.waitForTimeout(600);

const catalogue = await (await fetch(`${BASE}/api/v1/profiles`)).json();
const profileCards = await page.locator('[role="radio"][aria-checked]').count();
ok('profile picker renders every catalogue profile + 2 numeric modes',
   profileCards === catalogue.count + 2,
   `radios=${profileCards} catalogue=${catalogue.count}`);
ok('catalogue is the expanded lexicon (>= 10 profiles, >= 100k surrogates)',
   catalogue.count >= 10 && catalogue.lexicon.total_unique_surrogates >= 100000,
   `profiles=${catalogue.count} surrogates=${catalogue.lexicon.total_unique_surrogates}`);
ok('surrogate capacity badge shown', await page.locator('text=/surrogates/').first().isVisible());

// select one of the NEW v2 domains
await page.click('text=Biodefence');
await page.waitForTimeout(350);
ok('new biodefence domain selectable',
   await page.locator('[role="radio"][aria-checked="true"]:has-text("Biodefence")').isVisible());

// switch back to the defense profile for the canonical round-trip
await page.click('text=Kinetic Defense');
await page.waitForTimeout(350);

await page.fill('input[type=password]', 'Air-Gapped-Vault-2026!');
await page.waitForTimeout(400);
ok('passphrase strength meter appears', await page.locator('[role="progressbar"]').first().isVisible());
await page.fill('#seed', 'v2-live');
await page.screenshot({ path: `${SHOTS}/v2-3-transform.png`, fullPage: true });

/* ===================== STAGE 4 : VAULT ===================== */
await page.click('button:has-text("Mask & seal vault")');
await page.waitForSelector('text=Isomorphism verified', { timeout: 120000 });
await page.waitForTimeout(1200);

ok('isomorphism verified banner', await page.locator('text=Isomorphism verified').isVisible());
const inv = await page.locator('text=/invariants hold/').innerText();
ok('all invariants hold', /(\d+) of \1 invariants hold/.test(inv.replace(/,/g, '')), inv);

ok('parity chart section present', await page.locator('text=Analytical parity proof').isVisible());
const sigma = await page.locator('text=/Σ\\|Δ\\|/').first().innerText();
ok('aggregate parity exact (sum |delta| = 0)', /Σ\|Δ\| = 0/.test(sigma), sigma);

ok('split compare present', await page.locator('text=CONFIDENTIAL SOURCE').isVisible());
ok('sanitized side present', await page.locator('text=SANITIZED COVER').isVisible());
ok('column ledger present', await page.locator('text=Column transformation ledger').isVisible());
ok('AES-256-GCM badge shown', await page.locator('text=/AES-256-GCM/').first().isVisible());

// exercise the chart tab switch (shared layoutId pill)
await page.click('button[role="tab"]:has-text("Trend")');
await page.waitForTimeout(600);
ok('trend chart renders', (await page.locator('.recharts-line').count()) >= 2);
await page.screenshot({ path: `${SHOTS}/v2-4-vault.png`, fullPage: true });

// grid sorting works (TanStack v9)
await page.click('button[role="tab"]:has-text("Aggregates")');
await page.waitForTimeout(400);
const th = page.locator('th button').first();
await th.click();
await page.waitForTimeout(400);
const sortState = await page.locator('th[aria-sort]').first().getAttribute('aria-sort');
ok('TanStack v9 sorting works', sortState === 'ascending' || sortState === 'descending', `aria-sort=${sortState}`);

/* ===================== STAGE 5 : RESTORE ===================== */
await page.locator('main button', { hasText: 'Verify round-trip' }).click();
await page.waitForSelector('text=Lossless re-identification', { timeout: 20000 });
await page.waitForTimeout(700);
ok('restore stage handoff carried artifact + vault',
   await page.locator('text=/\\.ciphermap|\\.json/').first().isVisible());

await page.locator('main button', { hasText: /^Re-identify$/ }).click();
await page.locator('main').locator('text=Re-identification complete').first().waitFor({ timeout: 120000 });
await page.waitForTimeout(900);
ok('re-identification complete', await page.locator('main').locator('text=Re-identification complete').first().isVisible());
const restored = await page.locator('text=/values and/').innerText();
ok('values restored reported', /\d/.test(restored), restored.replace(/\n/g, ' '));
ok('restored grid rendered', await page.locator('text=Restored dataset').isVisible());
await page.screenshot({ path: `${SHOTS}/v2-5-restore.png`, fullPage: true });

/* ===================== ATTESTATION DRAWER ===================== */
await page.click('button[title="Open the air-gap attestation report"]');
await page.waitForTimeout(700);
ok('attestation drawer opens', await page.locator('[aria-label="Air-gap attestation"]').isVisible());
ok('browser-observed egress section', await page.locator('text=Browser-observed network').isVisible());
ok('drawer reports NONE external', await page.locator('text=NONE').first().isVisible());
ok('lexicon capacity in drawer', await page.locator('text=Offline lexicon capacity').isVisible());
await page.screenshot({ path: `${SHOTS}/v2-6-attestation.png`, fullPage: true });
await page.keyboard.press('Escape');
await page.locator('[role="dialog"][aria-label="Air-gap attestation"]')
  .waitFor({ state: 'hidden', timeout: 10000 });
ok('attestation drawer closes on Escape (keyboard dialog contract)', true);

/* ===================== COMMAND PALETTE (v2.1) ===================== */
await page.keyboard.press('Control+k');
await page.waitForTimeout(500);
const palette = page.locator('[role="dialog"][aria-label="Command palette"]');
ok('Ctrl-K opens the command palette', await palette.isVisible().catch(() => false));

const paletteInput = page.locator('input[role="combobox"]').first();
ok('palette input is a WAI-ARIA combobox and holds focus',
   await paletteInput.evaluate((el) => el === document.activeElement).catch(() => false));
ok('palette exposes aria-activedescendant for roving virtual focus',
   (await paletteInput.getAttribute('aria-activedescendant')) !== null);

await paletteInput.fill('vault');
await page.waitForTimeout(350);
const hits = await page.locator('[role="option"]').count();
ok('palette fuzzy-filters commands', hits > 0 && hits < 20, `options=${hits}`);
await page.screenshot({ path: `${SHOTS}/v2-8-command-palette.png` });

await page.keyboard.press('Escape');
await palette.waitFor({ state: 'hidden', timeout: 10000 });
ok('Escape closes the palette', !(await palette.isVisible().catch(() => false)));
// Focus restore only has a meaningful target when the palette is opened from a
// real control (hotkey-opened, document.body is the prior activeElement).
const cmdTrigger = page.locator('header button', { hasText: /Commands/ }).first();
await cmdTrigger.click();
await palette.waitFor({ state: 'visible', timeout: 10000 });
await page.keyboard.press('Escape');
await palette.waitFor({ state: 'hidden', timeout: 10000 });
await page.waitForTimeout(250);
ok('focus is restored to the invoking trigger after the palette closes',
   await cmdTrigger.evaluate((el) => el === document.activeElement));

/* ===================== AUDIT STAGE (v2.1) ===================== */
await page.locator('nav button, aside button').filter({ hasText: /Verify independently|Audit/i }).first()
  .click().catch(async () => {
    await page.locator('button', { hasText: /Audit/i }).first().click();
  });
await page.waitForTimeout(700);
ok('audit stage renders the independent isomorphism auditor',
   await page.locator('text=/independent isomorphism audit/i').first().isVisible().catch(() => false));
ok('audit stage offers three drop zones + passphrase',
   (await page.locator('input[type="file"]').count()) >= 3,
   `dropzones=${await page.locator('input[type="file"]').count()}`);
await page.screenshot({ path: `${SHOTS}/v2-9-audit.png`, fullPage: true });

/* ===================== REDUCED MOTION ===================== */
const ctx2 = await browser.newContext({ viewport: { width: 1400, height: 900 }, reducedMotion: 'reduce' });
const p2 = await ctx2.newPage();
await p2.goto(BASE, { waitUntil: 'networkidle' });
await p2.waitForTimeout(800);
ok('renders correctly under prefers-reduced-motion',
   await p2.locator('text=AetherMask').first().isVisible());
await p2.screenshot({ path: `${SHOTS}/v2-7-reduced-motion.png` });
await ctx2.close();

/* ===================== AIR-GAP VERDICT ===================== */
ok('NO external network requests', external.length === 0,
   external.length ? external.slice(0, 5).join(', ') : 'none');
ok('no console/page errors', consoleErrors.length === 0,
   consoleErrors.slice(0, 3).join(' | '));

console.log(`\nTotal requests observed: ${allReqs.length}`);
console.log(`External requests:       ${external.length}`);

const passed = results.filter((r) => r.pass).length;
console.log(`\n${'='.repeat(64)}`);
console.log(passed === results.length
  ? `  ALL ${results.length} UI CHECKS PASSED`
  : `  ${passed}/${results.length} PASSED`);
results.filter(r => !r.pass).forEach(r => console.log(`    FAIL: ${r.name} [${r.extra}]`));
console.log('='.repeat(64));

await browser.close();
process.exit(passed === results.length ? 0 : 1);
