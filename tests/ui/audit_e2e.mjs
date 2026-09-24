/* End-to-end exercise of the v2.1 audit stage: run a real masking pass, then
   feed original + artifact + vault back through /verify via the GUI. */
import { chromium } from 'playwright';

const BASE = 'http://127.0.0.1:8000';
const SHOTS = '/home/user/.probe/shots';
const browser = await chromium.launch({ args: ['--no-sandbox'] });
const page = await (await browser.newContext({ viewport: { width: 1600, height: 1000 } })).newPage();
const external = [];
page.on('request', (r) => {
  const u = r.url();
  if (!u.startsWith(BASE) && !u.startsWith('data:') && !u.startsWith('blob:')) external.push(u);
});
const errs = [];
page.on('pageerror', (e) => errs.push(e.message));

const results = [];
const ok = (n, c, x = '') => { results.push({ n, c: !!c, x }); console.log(`${c ? 'PASS' : 'FAIL'}  ${n}${x ? `  [${x}]` : ''}`); };

await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(800);

// 1. produce a real masked artifact + vault
await page.setInputFiles('input[type=file]', '/home/user/aethermask/samples/classified_missions.csv');
await page.waitForTimeout(1200);
await page.click('button:has-text("Analyse sensitivity")');
await page.waitForSelector('text=/risk score/', { timeout: 60000 });
await page.waitForTimeout(600);
await page.click('button:has-text("Configure transform")');
await page.waitForSelector('text=Cover domain profile', { timeout: 30000 });
await page.waitForTimeout(600);
await page.fill('input[type=password]', 'Audit-Stage-Passphrase-2026!');
await page.waitForTimeout(300);
await page.click('button:has-text("Mask & seal vault")');
await page.waitForSelector('text=Isomorphism verified', { timeout: 120000 });
ok('masking pass produced a sealed artifact', true);

// 2. jump to audit and use the session-handoff button
await page.locator('nav[aria-label="Pipeline stage"] button', { hasText: /Verify independently/i }).click();
await page.waitForTimeout(700);
ok('audit stage reachable from the rail',
   await page.locator('text=/independent isomorphism audit/i').first().isVisible());

await page.locator('button', { hasText: /Load from this session/i }).click();
await page.waitForTimeout(900);
ok('session handoff populated the three audit inputs',
   (await page.locator('text=/classified_missions/i').count()) >= 1);

// 3. run the independent verification
await page.locator('main button', { hasText: /^Run independent audit$|^Verify$|^Run audit$/ }).first().click();
await page.waitForTimeout(3000);
await page.waitForSelector('text=/isomorphism holds|checks passed|verification passed|PASSED/i', { timeout: 120000 });
const verdict = (await page.locator('main').innerText()).replace(/\n/g, ' ');
ok('independent audit returns a PASSED verdict',
   /Audit passed/i.test(verdict), verdict.match(/Audit \w+[^.]{0,60}/i)?.[0] ?? '');

// "N of M checks" is the panel's own phrasing; require N === M and M > 0.
const m = /([\d,]+)\s+of\s+([\d,]+)\s+(?:recomputed|check)/i.exec(verdict);
const got = m ? Number(m[1].replace(/,/g, '')) : -1;
const tot = m ? Number(m[2].replace(/,/g, '')) : -1;
ok('every independent check passed', tot > 0 && got === tot, m ? `${got}/${tot}` : 'no N-of-M found');
ok('no discrepancies reported', !/discrepancy/i.test(verdict));

await page.screenshot({ path: `${SHOTS}/v2-10-audit-verdict.png`, fullPage: true });

ok('audit flow made zero external requests', external.length === 0, external.slice(0, 3).join(','));
ok('no page errors during audit flow', errs.length === 0, errs.slice(0, 2).join(' | '));

const passed = results.filter((r) => r.c).length;
console.log(`\n${'='.repeat(60)}`);
console.log(passed === results.length ? `  ALL ${results.length} AUDIT E2E CHECKS PASSED` : `  ${passed}/${results.length} PASSED`);
results.filter((r) => !r.c).forEach((r) => console.log(`    FAIL: ${r.n} [${r.x}]`));
console.log('='.repeat(60));
await browser.close();
process.exit(passed === results.length ? 0 : 1);
