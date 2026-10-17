import puppeteer from "puppeteer-core";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const URL = process.env.URL || "http://localhost:5180/";

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: "new",
  args: ["--no-sandbox", "--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"],
});
const page = await browser.newPage();
await page.setViewport({ width: 1600, height: 900, deviceScaleFactor: 1 });

const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push("console.error: " + m.text()); });
page.on("pageerror", (e) => errors.push("pageerror: " + e.message));

await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 30000 });
await new Promise((r) => setTimeout(r, 2500));

// Trigger the Base scenario, then the Storm scenario.
async function clickTrig(label) {
  const ok = await page.evaluate((lab) => {
    const btn = [...document.querySelectorAll(".trig")].find((b) => b.textContent.includes(lab));
    if (btn) { btn.click(); return true; } return false;
  }, label);
  return ok;
}
await clickTrig("Base");
await new Promise((r) => setTimeout(r, 2500));
await clickTrig("Storm");
await new Promise((r) => setTimeout(r, 3000));

const canvasOk = await page.evaluate(() => {
  const c = document.querySelector("canvas");
  return !!c && c.width > 100 && c.height > 100;
});
const scoreText = await page.evaluate(() => {
  const el = [...document.querySelectorAll(".readout .cell.total .v")][0];
  return el ? el.textContent : null;
});
const logCount = await page.evaluate(() => document.querySelectorAll(".log .row").length);

await page.screenshot({ path: "smoke.png" });
await browser.close();

console.log(JSON.stringify({ canvasOk, scoreText, logCount, errors }, null, 2));
if (!canvasOk || errors.length) process.exit(1);
