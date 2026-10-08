// Each entry returns an array of failed expectations (empty = pass).
const expect = (cond, msg, out) => { if (!cond) out.push(msg); };

export default {
  '01-': async (page, vp) => {
    const out = [];
    expect(await page.locator('#menu-panel .menu-item').count() === 6, 'kopi tab should show 6 items', out);
    await page.click('#tab-makanan');
    expect(await page.locator('#menu-panel .menu-item').count() === 4, 'makanan tab should show 4 items', out);
    expect((await page.textContent('#menu-panel')).includes('Rp'), 'prices formatted as Rupiah', out);
    expect((await page.textContent('#open-status')).length > 10, 'open status rendered', out);
    if (vp === 'mobile') {
      await page.click('.menu-toggle');
      expect(await page.locator('#nav-links').isVisible(), 'mobile menu opens', out);
      await page.click('#nav-links a[href="#menu"]');
      expect(!(await page.locator('#nav-links').isVisible()), 'mobile menu closes after link click', out);
    }
    return out;
  },
  '02-': async (page) => {
    const out = [];
    expect(await page.locator('.project').count() === 6, 'all 6 projects shown', out);
    await page.click('.chip:has-text("Laravel")');
    expect(await page.locator('.project').count() === 2, 'Laravel filter shows 2', out);
    const before = await page.getAttribute('html', 'data-theme');
    await page.click('#theme-toggle');
    expect(before !== await page.getAttribute('html', 'data-theme'), 'theme toggles', out);
    await page.reload();
    expect(before !== await page.getAttribute('html', 'data-theme'), 'theme persists after reload', out);
    await page.click('button[type="submit"]');
    expect((await page.textContent('#email-error')).length > 0, 'empty form shows email error', out);
    await page.fill('#name', 'Budi');
    await page.fill('#email', 'budi@contoh.id');
    await page.fill('#message', 'Halo Raka, saya ingin membuat website untuk toko saya.');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(900);
    expect((await page.textContent('#form-status')).includes('Terima kasih'), 'valid form shows success', out);
    return out;
  },
  '03-': async (page) => {
    const out = [];
    for (const t of ['Belajar CSS Grid', 'Beli kopi', 'Kirim laporan']) {
      await page.fill('#new-text', t);
      await page.press('#new-text', 'Enter');
    }
    expect(await page.locator('.todo').count() === 3, 'three todos added', out);
    await page.locator('.todo:has-text("Beli kopi") .toggle').check();
    await page.click('[data-filter="done"]');
    expect(await page.locator('.todo').count() === 1, 'done filter shows 1', out);
    await page.click('[data-filter="all"]');
    await page.locator('.todo:has-text("Kirim laporan") .text').dblclick();
    await page.fill('.edit-input', 'Kirim laporan bulanan');
    await page.press('.edit-input', 'Enter');
    expect(await page.locator('.todo:has-text("Kirim laporan bulanan")').count() === 1, 'edit saved', out);
    await page.locator('.todo:has-text("Belajar CSS Grid") .edit').click();
    await page.fill('.edit-input', 'batal');
    await page.press('.edit-input', 'Escape');
    expect(await page.locator('.todo:has-text("Belajar CSS Grid")').count() === 1, 'escape cancels edit', out);
    await page.reload();
    expect(await page.locator('.todo').count() === 3, 'todos persist after reload', out);
    await page.click('#clear-done');
    expect(await page.locator('.todo').count() === 2, 'clear done removes 1', out);
    await page.locator('.todo:has-text("Belajar CSS Grid") .delete').click();
    expect((await page.textContent('#counter')).startsWith('1 '), 'counter shows 1 left', out);
    return out;
  },
  '04-': async (page) => {
    const out = [];
    const press = async (keys) => { for (const k of keys) await page.keyboard.press(k); };
    const result = () => page.textContent('#result');
    await press(['2', '+', '3', '*', '4', 'Enter']);
    expect(await result() === '14', `2+3*4 should be 14, got ${await result()}`, out);
    await press(['Escape', '0', '.', '1', '+', '0', '.', '2', 'Enter']);
    expect(await result() === '0,3', `0.1+0.2 should be 0,3, got ${await result()}`, out);
    await press(['Escape', '5', '/', '0', 'Enter']);
    expect((await result()).includes('nol'), 'divide by zero message', out);
    await press(['7']);
    expect(await result() === '7', 'typing after error starts fresh', out);
    await press(['Escape', '1', '2', '3', '4', '5', '6', '7', 'Enter']);
    expect(await result() === '1.234.567', `grouping, got ${await result()}`, out);
    await page.click('[data-action="clear"]');
    await page.click('[data-digit="5"]');
    await page.click('[data-digit="0"]');
    await page.click('[data-action="percent"]');
    expect(await result() === '0,5', `50% should be 0,5, got ${await result()}`, out);
    await page.click('[data-action="negate"]');
    await page.click('[data-op="×"]');
    await page.click('[data-digit="4"]');
    await page.click('[data-action="equals"]');
    expect(await result() === '−2', `-0.5*4 should be −2, got ${await result()}`, out);
    await press(['Escape', '9', '-', '1', '0', 'Backspace', 'Enter']);
    expect(await result() === '8', `9-10 backspace -> 9-1 = 8, got ${await result()}`, out);
    return out;
  },
  '05-': async (page, vp) => {
    const out = [];
    expect(await page.locator('#stats .card').count() === 4, '4 stat cards', out);
    expect(await page.locator('#chart .bar').count() === 12, '12 bars', out);
    expect(await page.locator('#tbody tr').count() === 10, '10 rows', out);
    await page.fill('#search', 'siti');
    expect(await page.locator('#tbody tr').count() === 1, 'search narrows to 1', out);
    await page.fill('#search', 'zzz');
    expect((await page.textContent('#tbody')).includes('Tidak ada'), 'empty state', out);
    await page.fill('#search', '');
    await page.click('th[data-key="total"] button');
    expect((await page.textContent('#tbody tr:first-child')).includes('98.000'), 'sort total ascending', out);
    await page.click('th[data-key="total"] button');
    expect((await page.textContent('#tbody tr:first-child')).includes('2.150.000'), 'sort total descending', out);
    await page.locator('#chart .bar').nth(11).hover().catch(() => {});
    if (vp === 'mobile') {
      await page.click('#menu-btn');
      await page.waitForTimeout(350);
      const box = await page.locator('#sidebar').boundingBox();
      expect(box && box.x >= 0, 'sidebar slides in on mobile', out);
    }
    return out;
  },
  '06-': async (page) => {
    const out = [];
    await page.click('#start-btn');
    for (let i = 0; i < 10; i++) {
      await page.locator('.option').first().click();
      expect((await page.textContent('#feedback')).length > 0, `feedback after answer ${i + 1}`, out);
      await page.click('#next-btn');
    }
    expect(await page.isVisible('#result-screen'), 'result screen shown', out);
    expect(/\d+ \/ 10/.test(await page.textContent('#score')), 'score format', out);
    expect(await page.locator('#review li').count() === 10, 'review has 10 items', out);
    return out;
  },
  '07-': async (page) => {
    const out = [];
    await page.click('#play-btn');
    await page.waitForTimeout(300);
    expect(await page.isHidden('#overlay'), 'overlay hides on start', out);
    await page.keyboard.press(' ');
    expect((await page.textContent('#overlay-title')) === 'Jeda', 'space pauses', out);
    await page.keyboard.press(' ');
    await page.keyboard.press('ArrowLeft'); // reversal ignored
    await page.waitForTimeout(2600);
    expect((await page.textContent('#overlay-title')) === 'Game over', 'hits wall -> game over', out);
    await page.click('#play-btn');
    await page.waitForTimeout(200);
    expect(await page.isHidden('#overlay'), 'restart works', out);
    return out;
  },
  '08-': async (page, vp) => {
    const out = [];
    if (vp !== 'desktop') return out;
    for (let game = 0; game < 4; game++) {
      for (let guard = 0; guard < 9; guard++) {
        await page.waitForFunction(() => document.querySelector('#status').textContent !== 'Komputer berpikir…');
        const free = await page.$$('.cell:not(:disabled)');
        if (!free.length) break;
        await free[Math.floor(Math.random() * free.length)].click();
        await page.waitForTimeout(450);
      }
      await page.click('#restart');
      await page.waitForTimeout(450);
    }
    expect((await page.textContent('#score-x')) === '0', 'human never beats minimax', out);
    const total = ['#score-x', '#score-o', '#score-draw'];
    let sum = 0;
    for (const s of total) sum += Number(await page.textContent(s));
    expect(sum === 4, `4 games finished, got ${sum}`, out);
    return out;
  },
  '09-': async (page) => {
    const out = [];
    await page.clock.install();
    await page.reload();
    expect((await page.textContent('#time')) === '25:00', 'starts at 25:00', out);
    await page.click('#start-btn');
    await page.clock.fastForward('01:00');
    expect((await page.textContent('#time')) === '24:00', `after 1 min shows 24:00, got ${await page.textContent('#time')}`, out);
    await page.click('#start-btn'); // jeda
    await page.clock.fastForward('05:00');
    expect((await page.textContent('#time')) === '24:00', 'paused timer does not move', out);
    await page.click('#start-btn');
    await page.clock.fastForward('24:01');
    expect((await page.textContent('#mode-label')) === 'Istirahat sebentar', 'auto switches to short break', out);
    expect((await page.textContent('#sessions')).includes('1'), 'session counted', out);
    for (let i = 0; i < 3; i++) await page.click('#skip-btn'), await page.click('#skip-btn');
    expect((await page.textContent('#mode-label')) === 'Istirahat panjang', `4th focus -> long break, got ${await page.textContent('#mode-label')}`, out);
    await page.click('summary');
    await page.fill('#set-long', '20');
    await page.dispatchEvent('#set-long', 'change');
    expect((await page.textContent('#time')) === '20:00', 'duration setting applies', out);
    return out;
  },
  '10-': async (page) => {
    const out = [];
    expect(/Rp\s99\.000/.test(await page.textContent('#plans')), 'monthly Pro price', out);
    await page.click('#billing-switch');
    const text = await page.textContent('#plans');
    expect(/Rp\s79\.000/.test(text) && text.includes('948.000'), 'yearly Pro price', out);
    expect((await page.getAttribute('#billing-switch', 'aria-checked')) === 'true', 'switch aria-checked', out);
    await page.click('summary:has-text("tersembunyi")');
    expect(await page.isVisible('details[open] p'), 'faq opens', out);
    expect(await page.locator('#compare-body tr').count() === 7, 'compare rows', out);
    return out;
  },
  '11-': async (page) => {
    const out = [];
    expect(await page.locator('.product').count() === 8, '8 products', out);
    await page.click('#categories button:has-text("Kain")');
    expect(await page.locator('.product').count() === 2, 'Kain filter', out);
    await page.click('#categories button:has-text("Semua")');
    await page.fill('#search', 'lasem');
    expect(await page.locator('.product').count() === 1, 'search lasem', out);
    await page.click('.add-btn');
    await page.click('.add-btn');
    await page.fill('#search', 'kawung');
    await page.click('.add-btn');
    expect((await page.textContent('#cart-count')) === '3', 'cart count 3', out);
    await page.reload();
    expect((await page.textContent('#cart-count')) === '3', 'cart persists', out);
    await page.click('#open-cart');
    expect(await page.isVisible('#cart'), 'cart dialog opens', out);
    expect((await page.textContent('#cart-total')).includes('1.369.000'), `total 540000*2+289000, got ${await page.textContent('#cart-total')}`, out);
    await page.locator('.cart-item').first().locator('[data-step="-1"]').click();
    expect((await page.textContent('#cart-count')) === '2', 'decrement works', out);
    await page.click('#checkout');
    expect((await page.textContent('#checkout-note')).includes('WHATSAPP_NUMBER'), 'checkout without number explains config', out);
    await page.keyboard.press('Escape');
    expect(!(await page.isVisible('#cart')), 'Esc closes dialog', out);
    return out;
  },
  '12-': async (page) => {
    const out = [];
    const monthly = await page.textContent('#monthly');
    // P = 600 jt, r = 7,5%/12, n = 180 -> ~Rp5.562.0xx
    expect(/Rp\s?5\.56\d\.\d{3}/.test(monthly), `monthly payment ~5,56 jt, got ${monthly}`, out);
    expect(await page.locator('#schedule tr').count() === 15, '15 yearly rows', out);
    expect(/^Rp\s0$/.test((await page.textContent('#schedule tr:last-child td:last-child')).trim()), 'balance ends at 0', out);
    await page.fill('#rate', '0');
    expect((await page.textContent('#monthly')).includes('3.333.333'), 'zero rate = P/n', out);
    await page.fill('#tenor', '40');
    expect((await page.textContent('#error')).includes('1–30'), 'tenor validation', out);
    expect((await page.getAttribute('#tenor', 'aria-invalid')) === 'true', 'aria-invalid on tenor', out);
    return out;
  },
  '13-': async (page) => {
    const out = [];
    expect(await page.locator('#toc-list a').count() === 7, `toc has 7 links, got ${await page.locator('#toc-list a').count()}`, out);
    expect(/\d+ menit baca/.test(await page.textContent('#reading-time')), 'reading time', out);
    await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'instant' }));
    await page.waitForTimeout(400);
    const scale = await page.evaluate(() => getComputedStyle(document.getElementById('progress')).transform);
    expect(scale.startsWith('matrix(1,'), `progress full at bottom, got ${scale}`, out);
    expect(await page.locator('#to-top.visible').count() === 1, 'to-top visible', out);
    expect(await page.locator('.toc a.active').count() === 1, 'one active toc link', out);
    await page.click('#to-top');
    await page.waitForTimeout(1500);
    expect(await page.evaluate(() => window.scrollY) < 5, 'back to top', out);
    return out;
  },
  '14-': async (page) => {
    const out = [];
    await page.click('#next');
    expect(await page.locator('[aria-invalid="true"]').count() === 3, 'step 1 empty -> 3 errors', out);
    await page.fill('#fullName', 'Siti Aminah');
    await page.fill('#phone', '0812-3456-7890');
    await page.fill('#birthDate', '2015-01-01');
    await page.click('#next');
    expect((await page.textContent('.field:has(#birthDate) .error')).includes('17'), 'under 17 rejected', out);
    await page.fill('#birthDate', '1995-05-20');
    await page.click('#next');
    expect(await page.isVisible('#street'), 'moved to step 2', out);
    await page.fill('#street', 'Jl. Merdeka No. 10 RT 02/RW 05');
    await page.fill('#city', 'Bandung');
    await page.fill('#postalCode', '4011');
    await page.click('#next');
    expect(await page.isVisible('#street'), 'bad postal code blocks', out);
    await page.fill('#postalCode', '40115');
    await page.click('#next');
    await page.fill('#email', 'siti@contoh.id');
    await page.fill('#password', 'Rahasia123');
    await page.fill('#confirm', 'Rahasia124');
    await page.click('#next');
    expect((await page.textContent('.field:has(#confirm) .error')).includes('tidak sama'), 'password mismatch', out);
    await page.fill('#confirm', 'Rahasia123');
    await page.check('#terms');
    await page.click('#next');
    expect((await page.textContent('#summary')).includes('20 Mei 1995'), 'summary shows formatted date', out);
    await page.click('#summary button[aria-label="Ubah alamat"]');
    expect(await page.isVisible('#street'), 'edit jumps back to address', out);
    await page.click('#next'); await page.click('#next');
    await page.click('#next');
    expect((await page.textContent('#success-text')).includes('siti@contoh.id'), 'success shows email', out);
    return out;
  },
  '15-': async (page) => {
    const out = [];
    const url = page.url().split('?')[0] + '?to=' + encodeURIComponent('<img src=x onerror="window.__xss=1">Pak Budi');
    await page.goto(url);
    expect((await page.textContent('#guest-name')).includes('<img'), 'guest name rendered as text', out);
    expect(!(await page.evaluate(() => window.__xss)), 'no XSS from ?to=', out);
    await page.click('#open-invitation');
    await page.waitForTimeout(900);
    expect(!(await page.isVisible('#open-invitation')), 'cover hidden', out);
    expect(Number(await page.textContent('#cd-days')) > 0, 'countdown days > 0', out);
    await page.click('#rsvp button[type="submit"]');
    expect((await page.textContent('#rsvp-error')).length > 0, 'empty RSVP rejected', out);
    await page.fill('#rsvp-name', '<b>Rina</b>');
    await page.selectOption('#rsvp-attend', 'Tidak hadir');
    await page.fill('#rsvp-message', 'Selamat menempuh hidup baru!');
    await page.click('#rsvp button[type="submit"]');
    expect(await page.locator('#wishes li').count() === 1, 'wish added', out);
    expect((await page.textContent('#wishes li strong')) === '<b>Rina</b>', 'wish name escaped', out);
    expect((await page.textContent('#wishes .badge')) === 'Tidak hadir', 'badge for not attending', out);
    const download = page.waitForEvent('download', { timeout: 3000 });
    await page.click('#save-date');
    const d = await download;
    expect(d.suggestedFilename().endsWith('.ics'), 'ics downloaded', out);
    return out;
  },
  '16-': async (page, vp) => {
    const out = [];
    expect(await page.locator('#preview h1').count() === 1, 'sample renders h1', out);
    expect(await page.locator('#preview pre code.language-js').count() === 1, 'code block with language', out);
    expect(await page.locator('#preview ol li').count() === 3, 'ordered list', out);
    await page.fill('#editor', '# Uji\n\n<img src=x onerror="window.__xss=1">\n\n[klik](javascript:alert(1)) dan [aman](https://example.com)\n\n**tebal** *miring* `a*b*c`\n\n> kutipan\n\n---');
    await page.waitForTimeout(100);
    expect(!(await page.evaluate(() => window.__xss)), 'img onerror not executed', out);
    expect(await page.locator('#preview img').count() === 0, 'no img element created', out);
    const hrefs = await page.$$eval('#preview a', (as) => as.map((a) => a.getAttribute('href')));
    expect(hrefs[0] === '#' && hrefs[1] === 'https://example.com', `unsafe link neutralised, got ${hrefs}`, out);
    expect((await page.textContent('#preview code')) === 'a*b*c', 'inline code not formatted', out);
    expect(await page.locator('#preview blockquote').count() === 1 && await page.locator('#preview hr').count() === 1, 'quote and hr', out);
    await page.fill('#editor', 'halo');
    await page.click('#editor');
    await page.keyboard.press('ControlOrMeta+a');
    await page.click('[data-cmd="bold"]');
    expect((await page.inputValue('#editor')) === '**halo**', `bold wraps selection, got ${await page.inputValue('#editor')}`, out);
    await page.waitForTimeout(500);
    await page.reload();
    expect((await page.inputValue('#editor')) === '**halo**', 'content autosaved', out);
    if (vp === 'mobile') {
      expect(!(await page.isVisible('#preview')), 'mobile shows editor first', out);
      await page.click('.tabs [data-view="preview"]');
      expect(await page.isVisible('#preview'), 'mobile preview tab', out);
    } else {
      const download = page.waitForEvent('download', { timeout: 3000 });
      await page.click('#download');
      expect((await download).suggestedFilename() === 'catatan.md', 'download .md', out);
    }
    return out;
  },
  '17-': async (page, vp) => {
    const out = [];
    const countIn = (col) => page.locator(`.column[data-column="${col}"] .card`).count();
    expect(await countIn('todo') === 2 && await countIn('doing') === 1 && await countIn('done') === 1, 'sample cards', out);
    await page.fill('#add-todo', 'Uji kartu baru');
    await page.press('#add-todo', 'Enter');
    expect(await countIn('todo') === 3, 'card added', out);
    await page.click('.card:has-text("Uji kartu baru") button[aria-label*="ke Dikerjakan"]');
    expect(await countIn('doing') === 2, 'arrow button moves card', out);
    if (vp === 'desktop') {
      await page.dragAndDrop('.card:has-text("Siapkan database produk")', '.column[data-column="done"] .card:has-text("Riset")', { targetPosition: { x: 20, y: 5 } });
      expect(await countIn('done') === 2, 'drag moves card to done', out);
      const first = await page.textContent('.column[data-column="done"] .card p');
      expect(first === 'Siapkan database produk', `dropped above target, first is ${first}`, out);
    }
    await page.click('.card:has-text("Desain halaman beranda") .delete');
    expect(await page.locator('.card:has-text("Desain halaman beranda")').count() === 0, 'delete works', out);
    await page.reload();
    expect(await countIn('doing') === 1, 'state persisted', out);
    return out;
  },
  '18-': async (page, vp) => {
    const out = [];
    const text = await page.textContent('body');
    for (const banned of ['pasti menang', 'dijamin menang', '100%', 'terbaik di']) {
      expect(!text.toLowerCase().includes(banned), `no unethical claim "${banned}"`, out);
    }
    await page.click('#appointment button[type="submit"]');
    expect(await page.locator('#appointment [aria-invalid="true"]').count() === 7, `all 7 rules fire, got ${await page.locator('#appointment [aria-invalid="true"]').count()}`, out);
    await page.fill('#name', 'Andi Wijaya');
    await page.fill('#phone', '0812 3456 7890');
    await page.fill('#email', 'andi@example.com');
    await page.selectOption('#area', { index: 2 });
    // cari Sabtu berikutnya untuk uji aturan hari kerja
    const sat = await page.evaluate(() => { const d = new Date(); d.setDate(d.getDate() + ((6 - d.getDay() + 7) % 7 || 7)); return d.toISOString().slice(0, 10); });
    await page.fill('#date', sat);
    await page.fill('#summary', 'Saya di-PHK tanpa pesangon dan ingin tahu hak saya.');
    await page.click('#appointment button[type="submit"]');
    expect((await page.textContent('#date-error')).includes('Senin'), 'weekend rejected', out);
    const mon = await page.evaluate(() => { const d = new Date(); d.setDate(d.getDate() + ((1 - d.getDay() + 7) % 7 || 7)); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; });
    await page.fill('#date', mon);
    await page.click('#appointment button[type="submit"]');
    expect((await page.textContent('#consent-error')).includes('Persetujuan'), 'consent required', out);
    await page.check('#consent');
    await page.click('#appointment button[type="submit"]');
    expect((await page.textContent('#form-status')).includes('Senin'), 'success mentions Monday', out);
    if (vp === 'mobile') {
      await page.click('.menu-btn');
      expect(await page.isVisible('#links'), 'mobile menu opens', out);
    }
    return out;
  },
  '19-': async (page) => {
    const out = [];
    const pw = () => page.inputValue('#password');
    expect((await pw()).length === 16, 'default length 16', out);
    const p = await pw();
    expect(/[a-z]/.test(p) && /[A-Z]/.test(p) && /\d/.test(p) && /[^\w]/.test(p), 'contains every selected set', out);
    await page.fill('#length', '40');
    expect((await pw()).length === 40, 'length slider applies', out);
    for (const set of ['upper', 'digits', 'symbols']) await page.uncheck(`[data-set="${set}"]`);
    await page.click('[data-set="lower"]');
    expect(await page.isChecked('[data-set="lower"]'), 'cannot uncheck last set', out);
    expect(/^[a-z]+$/.test(await pw()), 'only lowercase now', out);
    await page.check('[data-set="digits"]');
    await page.check('#no-ambiguous');
    for (let i = 0; i < 20; i++) {
      await page.click('#generate');
      if (/[Il1O0o]/.test(await pw())) { out.push('ambiguous char leaked'); break; }
    }
    expect((await page.textContent('#strength-label')).length > 0, 'strength label', out);
    await page.click('#copy');
    await page.waitForTimeout(300);
    expect((await page.textContent('#copy-status')).length > 0, 'copy gives feedback', out);
    return out;
  },
  '20-': async (page) => {
    const out = [];
    await page.click('[data-seconds="15"]');
    const target = await page.textContent('#text');
    const firstWords = target.slice(0, 30);
    await page.click('#input');
    await page.keyboard.type(firstWords.slice(0, 20));
    await page.keyboard.type('xx');
    expect(await page.locator('#text span.wrong').count() >= 1, 'wrong chars highlighted', out);
    expect(await page.locator('#text span.correct').count() >= 19, 'correct chars highlighted', out);
    await page.waitForTimeout(16000);
    expect(await page.isVisible('#result'), 'result after 15s', out);
    expect(await page.isDisabled('#input'), 'input disabled after finish', out);
    expect(Number(await page.textContent('#result-wpm')) > 0, 'wpm > 0', out);
    await page.keyboard.press('Escape');
    expect(!(await page.isVisible('#result')) && (await page.inputValue('#input')) === '', 'Esc resets', out);
    return out;
  },
};
