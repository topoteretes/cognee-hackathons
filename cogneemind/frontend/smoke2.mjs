import puppeteer from "puppeteer-core";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const b = await puppeteer.launch({ executablePath: CHROME, headless: "new",
  args: ["--no-sandbox","--use-gl=swiftshader","--enable-webgl","--ignore-gpu-blocklist","--enable-unsafe-swiftshader"] });
const p = await b.newPage();
await p.setViewport({ width: 1680, height: 945, deviceScaleFactor: 1 });
await p.goto("http://localhost:5180/", { waitUntil: "domcontentloaded" });
await new Promise(r=>setTimeout(r,2500));
async function click(lab){ await p.evaluate(l=>{const x=[...document.querySelectorAll(".trig")].find(b=>b.textContent.includes(l)); x&&x.click();}, lab); }
await click("Base"); await new Promise(r=>setTimeout(r,2600));
await click("Storm"); await new Promise(r=>setTimeout(r,3200));
// run compounding
await p.evaluate(()=>{const x=[...document.querySelectorAll("button")].find(b=>b.textContent.includes("cold vs warm")); x&&x.click();});
await new Promise(r=>setTimeout(r,1500));
await p.screenshot({ path: "final.png" });
await b.close(); console.log("ok");
