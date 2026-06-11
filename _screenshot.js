
const {chromium} = require('playwright');
(async () => {
  const browser = await chromium.launch({headless: true});
  const page = await browser.newPage({viewport: {width: 1280, height: 800}});

  # Screenshot 1: homepage (search page)
  await page.goto('http://127.0.0.1:5173/', {waitUntil: 'networkidle', timeout: 15000});
  await page.screenshot({path: 'D:/gongju/gplay/.agents/skills/gplay-system/subskills/dev-server-workflow/scripts/screenshot-home.png', fullPage: true});

  # Screenshot 2: search for 000630
  await page.fill('input', '000630');
  await page.waitForTimeout(1000);
  await page.screenshot({path: 'D:/gongju/gplay/.agents/skills/gplay-system/subskills/dev-server-workflow/scripts/screenshot-search-000630.png', fullPage: true});

  # Screenshot 3: search for 600000
  await page.fill('input', '600000');
  await page.waitForTimeout(1000);
  await page.screenshot({path: 'D:/gongju/gplay/.agents/skills/gplay-system/subskills/dev-server-workflow/scripts/screenshot-search-600000.png', fullPage: true});

  # Screenshot 4: click on 600000 to go to detail page
  const cell = await page.locator('tr.clickable').first();
  await cell.click();
  await page.waitForTimeout(2000);
  await page.screenshot({path: 'D:/gongju/gplay/.agents/skills/gplay-system/subskills/dev-server-workflow/scripts/screenshot-detail-600000.png', fullPage: true});

  await browser.close();
  console.log('DONE');
})();
