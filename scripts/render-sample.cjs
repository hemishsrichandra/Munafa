const fs = require('node:fs');
const { chromium } = require('playwright');
(async()=>{
  const browser=await chromium.launch(process.env.PLAYWRIGHT_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH}:{});
  const page=await browser.newPage({viewport:{width:790,height:1000},deviceScaleFactor:1.5});
  await page.setContent(fs.readFileSync('samples/invoice-a104.html','utf8'));
  await page.screenshot({path:'samples/invoice-a104.png',fullPage:true});
  await browser.close();
})();
