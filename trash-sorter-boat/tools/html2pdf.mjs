// node html2pdf.mjs in.html out.pdf  (uses the Playwright install that ships with this environment)
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
const [, , src, out] = process.argv;
const b = await chromium.launch();
const p = await b.newPage();
await p.goto('file://' + src, { waitUntil: 'load' });
await p.pdf({ path: out, format: 'A4', printBackground: true, displayHeaderFooter: true,
  headerTemplate: '<span></span>',
  footerTemplate: '<div style="font-size:8px;width:100%;text-align:center;color:#777">Trash-sorting amphibious boat &middot; page <span class="pageNumber"></span> of <span class="totalPages"></span></div>',
  margin: { top: '16mm', bottom: '18mm', left: '15mm', right: '15mm' } });
await b.close();
