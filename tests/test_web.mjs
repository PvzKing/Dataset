// Uji semua website di examples/web dengan Chromium (desktop 1280px dan HP 375px).
// Pemakaian dari folder tests/:  npm install && npx playwright install chromium && node test_web.mjs [filter]
// Folder lain di examples/: WEB_DIR=web-pilihan node test_web.mjs [filter]
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { chromium } from 'playwright';
import baseInteractions from './interactions.mjs';
import pilihanInteractions from './interactions_pilihan.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const dir = path.join(here, '..', 'examples', process.env.WEB_DIR || 'web');
const interactions = { ...baseInteractions, ...pilihanInteractions };
const filter = process.argv[2] || '';
const shots = path.join(here, 'screenshots');
fs.mkdirSync(shots, { recursive: true });

// WebGL lewat SwiftShader supaya game 3D (26-) tetap jalan di Chromium headless tanpa GPU.
// Google Fonts hanya boleh di folder selain examples/web (web-pilihan memakainya, dengan font sistem sebagai cadangan).
// Website di examples/web adalah data latihan, jadi tetap tanpa request eksternal sama sekali.
const FONT_HOSTS = (process.env.WEB_DIR || 'web') === 'web' ? /^$/ : /^https:\/\/fonts\.(googleapis|gstatic)\.com\//;
// Di lingkungan dengan proxy keluar (mis. container cloud), Chromium perlu diarahkan ke proxy itu agar font termuat.
const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined;
const browser = await chromium.launch({ proxy, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
let failures = 0;

for (const file of fs.readdirSync(dir).filter((f) => f.endsWith('.html') && f.includes(filter)).sort()) {
  const url = pathToFileURL(path.join(dir, file)).href;
  const problems = [];
  for (const vp of [{ name: 'desktop', width: 1280, height: 800 }, { name: 'mobile', width: 375, height: 740 }]) {
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, ignoreHTTPSErrors: !!proxy });
    const page = await ctx.newPage();
    page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') problems.push(`[${vp.name}] console.${m.type()}: ${m.text()}`); });
    page.on('pageerror', (e) => problems.push(`[${vp.name}] pageerror: ${e.message}`));
    page.on('requestfailed', (r) => { if (!FONT_HOSTS.test(r.url())) problems.push(`[${vp.name}] requestfailed: ${r.url()}`); });
    page.on('request', (r) => { if (!r.url().startsWith('file:') && !r.url().startsWith('data:') && !r.url().startsWith('blob:') && !FONT_HOSTS.test(r.url())) problems.push(`[${vp.name}] external request: ${r.url()}`); });
    page.on('dialog', (d) => d.dismiss());
    await page.goto(url);
    await page.waitForTimeout(300);
    await page.evaluate(() => document.fonts.ready);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    if (overflow > 0) problems.push(`[${vp.name}] horizontal overflow ${overflow}px`);
    await page.screenshot({ path: path.join(shots, `${file.replace('.html', '')}-${vp.name}.png`), fullPage: vp.name === 'desktop' });
    const key = Object.keys(interactions).find((k) => file.startsWith(k));
    if (key) {
      try {
        const notes = await interactions[key](page, vp.name);
        if (notes && notes.length) problems.push(...notes.map((n) => `[${vp.name}] check: ${n}`));
      } catch (e) {
        problems.push(`[${vp.name}] interaction threw: ${e.message.split('\n')[0]}`);
      }
      await page.screenshot({ path: path.join(shots, `${file.replace('.html', '')}-${vp.name}-after.png`) });
    }
    await ctx.close();
  }
  if (problems.length) failures++;
  console.log(`${problems.length ? 'FAIL' : 'ok  '} ${file}`);
  for (const p of problems) console.log('     ' + p);
}
await browser.close();
process.exit(failures ? 1 : 0);
