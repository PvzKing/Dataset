// Skenario interaksi untuk examples/web-pilihan (kunci berawalan "p" supaya tidak bentrok dengan examples/web).
// Each entry returns an array of failed expectations (empty = pass).
const expect = (cond, msg, out) => { if (!cond) out.push(msg); };

export default {
  'p01-': async (page, vp) => {
    const out = [];
    expect(await page.locator('#works .work').count() === 6, 'all 6 works shown', out);
    await page.click('[data-filter="web"]');
    expect(await page.locator('#works .work').count() === 2, 'web filter shows 2', out);
    if (vp === 'mobile') {
      await page.click('#menu-toggle');
      expect(await page.locator('#nav-links').isVisible(), 'mobile menu opens', out);
      await page.click('#nav-links a[href="#kontak"]');
      expect(!(await page.locator('#nav-links').isVisible()), 'mobile menu closes after link', out);
    }
    await page.click('#contact-form button[type="submit"]');
    expect((await page.textContent('#email-error')).length > 0, 'empty form shows email error', out);
    await page.fill('#name', 'Budi');
    await page.fill('#email', 'budi@contoh.id');
    await page.click('#contact-form button[type="submit"]');
    expect((await page.textContent('#success')).includes('Budi'), 'valid form shows success', out);
    return out;
  },
  'p02-': async (page) => {
    const out = [];
    await page.fill('#city-input', 'Med');
    expect(await page.locator('#suggest li').count() === 1, 'search "Med" suggests one city', out);
    await page.press('#city-input', 'Enter');
    expect(await page.textContent('#city-name') === 'Medan', 'Enter picks Medan', out);
    const c = parseInt(await page.textContent('#temp'));
    await page.click('#unit-f');
    const f = parseInt(await page.textContent('#temp'));
    expect(Math.abs(f - (c * 9 / 5 + 32)) <= 1, `°F conversion (${c}°C -> ${f}°F)`, out);
    expect(await page.locator('#daily .day').count() === 7, '7-day forecast rendered', out);
    return out;
  },
  'p03-': async (page) => {
    const out = [];
    expect(await page.locator('#tracks .track').count() === 5, 'playlist has 5 tracks', out);
    await page.click('#play');
    expect(await page.getAttribute('#play', 'aria-label') === 'Jeda', 'play button turns into pause', out);
    await page.click('#next');
    expect(await page.textContent('#t-title') === 'Ombak Parangtritis', 'next track loads', out);
    await page.click('#play');
    expect(await page.getAttribute('#play', 'aria-label') === 'Putar', 'pause works', out);
    await page.click('#repeat');
    expect(await page.getAttribute('#repeat', 'aria-pressed') === 'true', 'repeat toggles', out);
    return out;
  },
  'p04-': async (page) => {
    const out = [];
    expect(await page.locator('#grid .card').count() === 9, 'all 9 recipes shown', out);
    await page.fill('#q', 'santan');
    expect(await page.locator('#grid .card').count() === 2, 'ingredient search "santan" finds 2', out);
    await page.fill('#q', '');
    await page.locator('#grid .heart').first().click();
    expect(await page.textContent('#fav-count') === '1', 'favourite counter', out);
    await page.locator('#grid .card').first().click();
    expect(await page.locator('#modal').isVisible(), 'recipe dialog opens', out);
    const before = await page.textContent('#m-ing');
    await page.click('#plus');
    expect(before !== await page.textContent('#m-ing'), 'portion scaling changes quantities', out);
    await page.click('#close');
    expect(!(await page.locator('#modal').isVisible()), 'dialog closes', out);
    return out;
  },
  'p05-': async (page) => {
    const out = [];
    expect(await page.locator('#dests .dest').count() === 10, '10 destinations', out);
    await page.selectOption('#island', 'Sulawesi');
    expect(await page.locator('#dests .dest').count() === 2, 'island filter', out);
    await page.selectOption('#island', '');
    await page.locator('#dests .add').first().click();
    expect(await page.locator('#trip li').count() === 1, 'destination added to plan', out);
    const t1 = await page.textContent('#total');
    await page.locator('#trip [data-inc]').click();
    expect((await page.textContent('#trip')).includes('3 malam'), 'nights increment', out);
    expect(t1 !== await page.textContent('#total'), 'total updates with nights', out);
    await page.reload();
    expect(await page.locator('#trip li').count() === 1, 'plan persists after reload', out);
    return out;
  },
  'p06-': async (page) => {
    const out = [];
    expect(await page.locator('#tx li').count() === 7, 'sample transactions', out);
    const before = await page.textContent('#expense');
    await page.fill('#amount', '50000');
    expect(await page.inputValue('#amount') === '50.000', 'amount gets thousand separators', out);
    await page.fill('#note', 'Kopi susu');
    await page.click('#form button[type="submit"]');
    expect(await page.locator('#tx li').count() === 8, 'transaction added', out);
    expect(before !== await page.textContent('#expense'), 'expense total updated', out);
    await page.fill('#search', 'Sewa');
    expect(await page.locator('#tx li').count() === 1, 'search filters list', out);
    await page.fill('#search', '');
    await page.locator('#tx .del').first().click();
    expect(await page.locator('#tx li').count() === 7, 'delete works', out);
    await page.click('#theme');
    expect(await page.getAttribute('html', 'data-theme') === 'dark', 'dark theme', out);
    return out;
  },
  'p07-': async (page) => {
    const out = [];
    expect(await page.locator('#board .card').count() === 16, '16 cards on medium', out);
    const pairs = await page.evaluate(() => deck.map((c) => c.pair));
    const done = new Set();
    for (let i = 0; i < pairs.length; i++) {
      if (done.has(i)) continue;
      const j = pairs.findIndex((p, k) => k !== i && p === pairs[i]);
      await page.locator('#board .card').nth(i).click();
      await page.locator('#board .card').nth(j).click();
      done.add(i); done.add(j);
    }
    await page.waitForTimeout(700);
    expect(await page.locator('#overlay.show').count() === 1, 'win overlay shows', out);
    expect((await page.textContent('#win-text')).includes('8 langkah'), 'perfect game takes 8 moves', out);
    return out;
  },
  'p08-': async (page) => {
    const out = [];
    expect(await page.locator('#tiles .tile').count() === 2, 'starts with two tiles', out);
    await page.evaluate(() => {
      tileEls.forEach((el) => el.remove()); tileEls.clear();
      grid = [[{ id: 900, v: 2 }, { id: 901, v: 2 }, null, null], [null, null, null, null], [null, null, null, null], [null, null, null, null]];
      score = 0; history = []; render();
    });
    await page.keyboard.press('ArrowLeft');
    expect(await page.textContent('#score') === '4', 'merging 2+2 scores 4', out);
    expect(await page.evaluate(() => grid[0][0].v === 4 && grid[0][0].merged), 'merged tile has value 4 at the left edge', out);
    await page.waitForTimeout(250); // ubin lama dihapus setelah animasi geser
    expect(await page.locator('#tiles .tile').count() === 2, 'merged tile plus one new tile on board', out);
    await page.click('#undo');
    expect(await page.textContent('#score') === '0', 'undo restores score', out);
    return out;
  },
  'p09-': async (page, vp) => {
    const out = [];
    if (vp === 'mobile') {
      await page.click('#menu-btn');
      expect(await page.locator('#menu').isVisible(), 'mobile menu opens', out);
      await page.click('#menu a[href="#reservasi"]');
    }
    expect(await page.isDisabled('#next'), 'next disabled before choosing', out);
    await page.locator('#svc-list .opt').first().click();
    await page.click('#next');
    await page.locator('#doc-list .opt').first().click();
    await page.click('#next');
    await page.locator('#dates .date:not([disabled])').first().click();
    await page.locator('#slots .slot:not([disabled])').first().click();
    await page.click('#next');
    await page.click('#next');
    expect((await page.textContent('#e-phone')).length > 0, 'phone validated', out);
    await page.fill('#p-name', 'Siti Aminah');
    await page.fill('#p-phone', '0812-3456-7890');
    await page.click('#next');
    expect((await page.textContent('#code')).startsWith('SS-'), 'booking code shown', out);
    expect((await page.textContent('#summary-final')).includes('Siti Aminah'), 'summary has patient name', out);
    return out;
  },
  'p10-': async (page) => {
    const out = [];
    const total = () => page.textContent('#total');
    expect(await total() === 'Rp46.900.000', `efisiensi rugi 6th4bln Rp7jt: ${await total()}`, out);
    await page.selectOption('#reason', 'pensiun');
    expect(await total() === 'Rp108.150.000', `pensiun 1,75x: ${await total()}`, out);
    expect((await page.textContent('#rows')).includes('Rp104.427.500'), 'layered pesangon tax applied', out);
    await page.selectOption('#reason', 'resign');
    expect(await total() === 'Rp1.400.000', `resign only UPH: ${await total()}`, out);
    expect(await page.locator('#pisah-label').isVisible(), 'uang pisah field shown for resign', out);
    await page.click('[data-k="pkwt"]');
    expect(await total() === 'Rp44.333.333', `PKWT kompensasi 76/12 x 7jt: ${await total()}`, out);
    await page.click('[data-k="pkwtt"]');
    await page.fill('#base', '');
    await page.fill('#allow', '');
    expect((await page.textContent('#err')).length > 0, 'missing wage shows error', out);
    return out;
  },
  'p11-': async (page) => {
    const out = [];
    expect(await page.locator('#habits .habit').count() === 3, 'three sample habits', out);
    await page.locator('#habits .check').first().click();
    expect(await page.textContent('#ring-count') === '1/3', 'ring counts done habit', out);
    await page.reload();
    expect(await page.textContent('#ring-count') === '1/3', 'progress persists', out);
    await page.fill('#habit-name', 'Jalan kaki pagi');
    await page.click('#add-form button[type="submit"]');
    expect(await page.locator('#habits .habit').count() === 4, 'habit added', out);
    expect(await page.textContent('#ring-count') === '1/4', 'ring total updates', out);
    await page.locator('#habits .del').last().click();
    expect(await page.locator('#habits .habit').count() === 4, 'first tap only asks for confirmation', out);
    await page.locator('#habits .del').last().click();
    expect(await page.locator('#habits .habit').count() === 3, 'second tap deletes the habit', out);
    return out;
  },
  'p12-': async (page) => {
    const out = [];
    expect(await page.evaluate(() => countSolutions(puzzle.slice()) === 1), 'puzzle has a unique solution', out);
    const right = await page.evaluate(() => solution[selected]);
    await page.keyboard.press(String(right));
    expect(await page.textContent('#mistakes') === '0', 'correct digit is not a mistake', out);
    await page.evaluate(() => { selected = cells.indexOf(0); render(); });
    const wrong = await page.evaluate(() => (solution[selected] % 9) + 1);
    await page.keyboard.press(String(wrong));
    expect(await page.textContent('#mistakes') === '1', 'wrong digit counts as mistake', out);
    expect(await page.locator('#board .cell.err').count() === 1, 'wrong cell highlighted', out);
    await page.click('#undo');
    expect(await page.locator('#board .cell.err').count() === 0, 'undo clears wrong digit', out);
    await page.click('#hint');
    expect(await page.evaluate(() => cells[selected] === solution[selected]), 'hint fills a correct digit', out);
    return out;
  },
  'p13-': async (page) => {
    const out = [];
    expect(await page.locator('.item:not(.hide)').count() === 16, '16 artworks', out);
    await page.click('[data-f="Kawung"]');
    expect(await page.textContent('#count') === '3 karya', 'style filter', out);
    await page.locator('.item:not(.hide)').first().click();
    expect(await page.locator('#lightbox.open').count() === 1, 'lightbox opens', out);
    await page.keyboard.press('ArrowRight');
    expect(await page.textContent('#lb-counter') === '2 / 3', 'arrow navigates', out);
    await page.click('#lb-like');
    await page.keyboard.press('Escape');
    expect(await page.locator('#lightbox.open').count() === 0, 'escape closes', out);
    await page.click('[data-f="Disukai"]');
    expect(await page.textContent('#count') === '1 karya', 'liked filter', out);
    return out;
  },
  'p14-': async (page) => {
    const out = [];
    await page.click('#tabs .tab:nth-child(3)');
    expect((await page.textContent('#feature')).includes('PPh 21'), 'payroll tab', out);
    await page.click('#billing');
    expect((await page.textContent('#plans')).includes('Rp12.000'), 'yearly price is 20% off', out);
    const before = await page.textContent('#save');
    await page.$eval('#emp', (el) => { el.value = 100; el.dispatchEvent(new Event('input')); });
    expect(before !== await page.textContent('#save'), 'savings calculator reacts', out);
    await page.click('#signup button');
    expect((await page.textContent('#form-msg')).includes('valid'), 'invalid email rejected', out);
    await page.fill('#email', 'owner@toko.id');
    await page.click('#signup button');
    expect((await page.textContent('#form-msg')).includes('owner@toko.id'), 'valid email accepted', out);
    await page.click('#clockin');
    expect(await page.locator('#log li').count() === 1, 'clock-in logs entry', out);
    return out;
  },
  'p15-': async (page) => {
    const out = [];
    expect(await page.locator('#jobs .job:not(.hidden)').count() === 2, 'two jobs shown initially', out);
    await page.click('#more');
    expect(await page.locator('#jobs .job:not(.hidden)').count() === 4, 'show all jobs', out);
    await page.click('[data-f="fintech"]');
    expect(await page.locator('#jobs .job').count() === 2, 'fintech filter', out);
    await page.click('#lang-btn');
    expect((await page.textContent('#jobs')).includes('Present'), 'English translation', out);
    await page.click('#theme-btn');
    const theme = await page.getAttribute('html', 'data-theme');
    await page.reload();
    expect(await page.getAttribute('html', 'data-theme') === theme, 'theme persists', out);
    return out;
  },
  'p16-': async (page) => {
    const out = [];
    const box = await page.locator('#canvas').boundingBox();
    const inked = () => page.evaluate(() => {
      const c = document.getElementById('canvas'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      for (let i = 0; i < d.length; i += 4) if (d[i] < 200) return true;
      return false;
    });
    expect(!(await inked()), 'canvas starts blank', out);
    await page.mouse.move(box.x + 30, box.y + 30);
    await page.mouse.down();
    await page.mouse.move(box.x + 120, box.y + 90, { steps: 8 });
    await page.mouse.up();
    expect(await inked(), 'drawing leaves ink', out);
    await page.click('#undo');
    expect(!(await inked()), 'undo clears stroke', out);
    await page.click('#redo');
    expect(await inked(), 'redo restores stroke', out);
    return out;
  },
  'p17-': async (page, vp) => {
    const out = [];
    if (vp === 'mobile') {
      expect(!(await page.locator('#chat').isVisible()), 'mobile starts on contact list', out);
      await page.locator('.contact', { hasText: 'Ibu' }).click();
    }
    const mine = () => page.locator('#msgs .msg.me').count();
    const theirs = () => page.locator('#msgs .msg.them').count();
    const m0 = await mine(), t0 = await theirs();
    await page.fill('#input', 'Halo Bu, sudah sampai rumah');
    await page.press('#input', 'Enter');
    expect(await mine() === m0 + 1, 'message sent', out);
    await page.waitForTimeout(3000);
    expect(await theirs() === t0 + 1, 'auto reply arrives', out);
    if (vp === 'mobile') await page.click('#back');
    await page.fill('#search', 'kurir');
    expect(await page.locator('.contact').count() === 1, 'contact search', out);
    return out;
  },
  'p18-': async (page) => {
    const out = [];
    expect(Number(await page.textContent('#cd-d')) >= 44, 'countdown shows days', out);
    await page.click('[data-inc="pro"]');
    expect(await page.textContent('#total') === 'Rp1.505.000', 'ticket + fee total', out);
    await page.fill('#promo', 'devid');
    await page.click('#apply');
    expect(await page.textContent('#total') === 'Rp1.355.000', 'promo 10% applied', out);
    await page.locator('#sessions [data-save]').first().click();
    expect((await page.textContent('#my-count')).includes('1 sesi'), 'session saved to agenda', out);
    await page.click('#buy');
    expect((await page.textContent('#done-code')).startsWith('NT26-'), 'ticket confirmation', out);
    await page.click('#close-done');
    return out;
  },
  'p19-': async (page) => {
    const out = [];
    expect(await page.inputValue('#to-v') === '1.000', '1 km = 1.000 m', out);
    await page.click('#swap');
    expect(await page.inputValue('#to-v') === '1', 'swap: 1.000 m = 1 km', out);
    await page.click('[data-cat="luas"]');
    await page.fill('#from-v', '2');
    expect(await page.inputValue('#to-v') === '28', '2 tumbak = 28 m²', out);
    expect(await page.locator('#note').isVisible(), 'land-unit note shown', out);
    await page.click('[data-cat="suhu"]');
    await page.fill('#from-v', '100');
    expect(await page.inputValue('#to-v') === '212', '100 °C = 212 °F', out);
    await page.fill('#to-v', '32');
    expect(await page.inputValue('#from-v') === '0', 'reverse: 32 °F = 0 °C', out);
    return out;
  },
  'p20-': async (page) => {
    const out = [];
    await page.click('#start');
    expect(await page.locator('#overlay').isHidden(), 'overlay hides on start', out);
    await page.keyboard.press('Space');
    await page.waitForTimeout(300);
    expect(await page.evaluate(() => balls.length === 1 && !balls[0].stuck), 'ball launched', out);
    await page.evaluate(() => { balls[0].y = H + 100; balls[0].vy = 1; });
    await page.waitForTimeout(200);
    expect(await page.textContent('#lives') === '❤❤', 'losing the ball costs a life', out);
    await page.evaluate(() => { bricks.forEach((b) => { b.hp = 0; }); });
    await page.waitForTimeout(200);
    expect((await page.textContent('#ov-text')).includes('Bonus'), 'clearing bricks completes level', out);
    return out;
  },
};
