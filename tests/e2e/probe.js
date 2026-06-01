const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ headless: true });
  const c = await b.newContext();
  const p = await c.newPage();
  const logs = [];
  p.on('console', m => logs.push(`[${m.type()}] ${m.text()}`));
  p.on('pageerror', e => logs.push(`[PAGEERR] ${e.message}`));
  p.on('requestfailed', r => logs.push(`[FAIL] ${r.url()} ${r.failure()?.errorText}`));
  // login
  const login = await (await p.request.post('http://localhost:16532/api/auth/login', {
    data: { username: 'admin', password: 'admin123' }
  })).json();
  await p.addInitScript(([t, u]) => {
    localStorage.setItem('token', t);
    localStorage.setItem('user', JSON.stringify(u));
  }, [login.token, login.user]);
  await p.goto('http://localhost:5173/video-management', { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(5000);
  const info = await p.evaluate(() => ({
    url: location.href,
    cards: document.querySelectorAll('.ant-card').length,
    tables: document.querySelectorAll('.ant-table-wrapper').length,
    empty: document.querySelectorAll('.ant-empty').length,
    spin: document.querySelectorAll('.ant-spin').length,
    rootHTML: document.getElementById('root')?.innerHTML?.slice(0, 500),
    bodyText: document.body.innerText.slice(0, 300),
  }));
  console.log(JSON.stringify(info, null, 2));
  console.log('--- LOGS ---');
  console.log(logs.slice(0, 30).join('\n'));
  await b.close();
})();
