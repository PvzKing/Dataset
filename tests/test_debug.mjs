// Uji sampel web_debug di data/train.jsonl:
// 1. Blok SEARCH/REPLACE di jawaban, bila diterapkan ke HTML ber-bug di prompt, menghasilkan salah satu website
//    di examples/web persis sama (website itu sendiri sudah diuji test_web.mjs).
// 2. Versi ber-bug benar-benar bermasalah di Chromium: ada error, scroll horizontal, atau skenario interaksi gagal.
// 3. Pemeriksaan khusus bug (EXTRA) lolos di versi asli.
// Pemakaian dari folder tests/:  node test_debug.mjs [filter-id]
import fs from 'fs';
import os from 'os';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { chromium } from 'playwright';
import interactions from './interactions.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const webDir = path.join(here, '..', 'examples', 'web');
const filter = process.argv[2] || '';
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'web-debug-'));
const FENCE = '`'.repeat(3);

// Pemeriksaan untuk bug yang tidak tertangkap skenario umum. Mengembalikan pesan jika gagal, atau null jika lolos.
const EXTRA = {
  'debug-001': async (page) => {
    await page.fill('#new-text', '<img src=x onerror="window.__xss=1">');
    await page.press('#new-text', 'Enter');
    await page.waitForTimeout(200);
    return (await page.evaluate(() => window.__xss)) ? 'XSS: onerror dijalankan' : null;
  },
  'debug-003': async (page) => {
    await page.click('#play-btn');
    await page.waitForTimeout(150);
    await page.keyboard.press('ArrowUp');
    await page.keyboard.press('ArrowLeft');
    await page.waitForTimeout(700);
    return (await page.isVisible('#overlay')) ? 'atas+kiri cepat menyebabkan game over' : null;
  },
  'debug-009': async (page) => {
    await page.fill('#editor', '[a](JavaScript:alert%281%29) [b](data:text/html,hai) [c](https://example.com)');
    await page.waitForTimeout(100);
    const hrefs = await page.$$eval('#preview a', (as) => as.map((a) => a.getAttribute('href')));
    return hrefs.join(' ') === '# # https://example.com' ? null : `href tidak aman lolos: ${hrefs}`;
  },
  'debug-010': async (page) => {
    await page.evaluate(() => localStorage.setItem('kanban-board-v1', 'undefined'));
    await page.reload();
    return (await page.locator('.card').count()) > 0 ? null : 'papan kosong saat localStorage rusak';
  },
  'debug-011': async (page) => {
    await page.addInitScript(() => { Math.random = () => 0; });
    await page.reload();
    const pw = await page.inputValue('#password');
    return new Set(pw).size >= 8 ? null : `password bergantung pada Math.random: ${pw}`;
  },
};

function applyPatches(html, answer) {
  const blocks = [...answer.matchAll(/<<<<<<< SEARCH\n([\s\S]*?)\n=======\n([\s\S]*?)\n>>>>>>> REPLACE/g)];
  if (!blocks.length) throw new Error('tidak ada blok SEARCH/REPLACE');
  for (const [, search, replace] of blocks) {
    const count = html.split(search).length - 1;
    if (count !== 1) throw new Error(`SEARCH harus cocok tepat 1 kali, ditemukan ${count}`);
    html = html.replace(search, () => replace);
  }
  return html;
}

async function problemsOf(browser, url, file, id) {
  const problems = [];
  for (const vp of [{ name: 'desktop', width: 1280, height: 800 }, { name: 'mobile', width: 375, height: 740 }]) {
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
    const page = await ctx.newPage();
    page.on('pageerror', (e) => problems.push(`[${vp.name}] pageerror: ${e.message}`));
    page.on('console', (m) => { if (m.type() === 'error') problems.push(`[${vp.name}] console.error: ${m.text()}`); });
    page.on('dialog', (d) => d.dismiss());
    await page.goto(url);
    await page.waitForTimeout(300);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    if (overflow > 0) problems.push(`[${vp.name}] horizontal overflow ${overflow}px`);
    const key = Object.keys(interactions).find((k) => file.startsWith(k));
    try {
      if (key) problems.push(...((await interactions[key](page, vp.name)) || []).map((n) => `[${vp.name}] check: ${n}`));
      await page.goto(url);
      await page.evaluate(() => localStorage.clear());
      await page.reload();
      const extra = EXTRA[id] && await EXTRA[id](page);
      if (extra) problems.push(`[${vp.name}] extra: ${extra}`);
    } catch (e) {
      problems.push(`[${vp.name}] threw: ${e.message.split('\n')[0]}`);
    }
    await ctx.close();
  }
  return problems;
}

const originals = Object.fromEntries(fs.readdirSync(webDir).filter((f) => f.endsWith('.html'))
  .map((f) => [fs.readFileSync(path.join(webDir, f), 'utf8').replace(/\n+$/, ''), f]));
const samples = fs.readFileSync(path.join(here, '..', 'data', 'train.jsonl'), 'utf8').split('\n').filter(Boolean)
  .map((l) => JSON.parse(l)).filter((s) => s.category === 'web_debug' && s.id.includes(filter));

const browser = await chromium.launch();
let failures = 0;
for (const s of samples) {
  const user = s.messages.find((m) => m.role === 'user').content;
  const answer = s.messages[s.messages.length - 1].content;
  const errors = [];
  const match = user.match(new RegExp(`${FENCE}html\\n([\\s\\S]*?)\\n${FENCE}`));
  const buggy = match ? match[1] : '';
  let file = null;
  try {
    file = originals[applyPatches(buggy, answer)];
    if (!file) errors.push('hasil patch tidak sama dengan website mana pun di examples/web');
  } catch (e) {
    errors.push(e.message);
  }
  let found = [];
  if (file) {
    const buggyPath = path.join(tmp, `${s.id}-${file}`);
    fs.writeFileSync(buggyPath, buggy + '\n');
    found = await problemsOf(browser, pathToFileURL(buggyPath).href, file, s.id);
    if (!found.length) errors.push('bug tidak terdeteksi: versi ber-bug lolos semua pemeriksaan');
    if (EXTRA[s.id]) {
      const ok = await problemsOf(browser, pathToFileURL(path.join(webDir, file)).href, file, s.id);
      errors.push(...ok.map((p) => `versi asli gagal: ${p}`));
    }
  }
  if (errors.length) failures++;
  console.log(`${errors.length ? 'FAIL' : 'ok  '} ${s.id} ${file || ''}`);
  for (const e of errors) console.log('     ' + e);
  if (!errors.length) console.log('     bug terdeteksi: ' + found[0]);
}
await browser.close();
fs.rmSync(tmp, { recursive: true, force: true });
console.log(`${samples.length} sampel web_debug diuji`);
process.exit(failures ? 1 : 0);
