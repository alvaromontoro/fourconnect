#!/usr/bin/env node

import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, normalize, resolve } from "node:path";
import process from "node:process";
import { chromium } from "playwright";

const ROOT = resolve(new URL("..", import.meta.url).pathname);
const DEFAULT_SIZE = 1000;
const FUTURE_NOW_ISO = "2100-01-01T00:00:00Z";

const MIME_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
  ".xml": "application/xml; charset=utf-8",
};

function parseArgs(argv) {
  const options = {
    date: null,
    gamePath: null,
    output: null,
    overwrite: false,
    size: DEFAULT_SIZE,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];

    if (arg === "--date") {
      options.date = argv[++i] || null;
      continue;
    }

    if (arg === "--path") {
      options.gamePath = argv[++i] || null;
      continue;
    }

    if (arg === "--output") {
      options.output = argv[++i] || DEFAULT_OUTPUT_FILE;
      continue;
    }

    if (arg === "--size") {
      const parsed = Number.parseInt(argv[++i] || "", 10);
      if (!Number.isInteger(parsed) || parsed < 100) {
        throw new Error("--size must be an integer >= 100");
      }
      options.size = parsed;
      continue;
    }

    if (arg === "--overwrite") {
      options.overwrite = true;
      continue;
    }

    if (arg === "--help" || arg === "-h") {
      printHelp();
      process.exit(0);
    }

    throw new Error(`Unknown argument: ${arg}`);
  }

  if (!options.date && !options.gamePath) {
    throw new Error("Provide --date YYYY-MM-DD or --path games/YYYY/MM/DD");
  }

  if (options.date && options.gamePath) {
    throw new Error("Use only one of --date or --path");
  }

  if (options.date && !/^\d{4}-\d{2}-\d{2}$/.test(options.date)) {
    throw new Error("--date must use format YYYY-MM-DD");
  }

  return options;
}

function printHelp() {
  console.log(`Usage:
  node bin/export-game-png.mjs --date YYYY-MM-DD [--output fourconnect-YYYY-MM-DD.png] [--size 1000] [--overwrite]
  node bin/export-game-png.mjs --path games/YYYY/MM/DD [--output fourconnect-YYYY-MM-DD.png] [--size 1000] [--overwrite]

Notes:
  - Saves a PNG in the game folder.
  - Adds body.export before capture.
  - Uses a mocked Date so future game pages do not redirect to home.`);
}

function dateFromGameDir(gameDir) {
  const rel = normalize(gameDir).replace(`${normalize(ROOT)}/`, "").replace(/\\/g, "/");
  const match = rel.match(/^games\/(\d{4})\/(\d{2})\/(\d{2})$/);
  if (!match) {
    return null;
  }
  return `${match[1]}-${match[2]}-${match[3]}`;
}

function gameDirFromDate(dateValue) {
  const [year, month, day] = dateValue.split("-");
  return resolve(ROOT, "games", year, month, day);
}

function gameDirFromPath(inputPath) {
  const trimmed = inputPath.replace(/^\.\//, "").replace(/\/$/, "");
  return resolve(ROOT, trimmed);
}

function toRoutePath(gameDir) {
  const rel = normalize(gameDir).replace(`${normalize(ROOT)}/`, "").replace(/\\/g, "/");
  if (!rel.startsWith("games/")) {
    throw new Error(`Game path must be inside ${join(ROOT, "games")}`);
  }
  return `/${rel}`;
}

async function pathExists(pathValue) {
  try {
    await stat(pathValue);
    return true;
  } catch {
    return false;
  }
}

function createStaticServer(rootDir) {
  return createServer(async (req, res) => {
    try {
      const requestUrl = new URL(req.url || "/", "http://localhost");
      let localPath = decodeURIComponent(requestUrl.pathname);

      if (localPath.endsWith("/")) {
        localPath = `${localPath}index.html`;
      }

      const normalizedPath = normalize(localPath).replace(/^([.]{2}[\/\\])+/, "");
      const absPath = resolve(rootDir, `.${normalizedPath.startsWith("/") ? normalizedPath : `/${normalizedPath}`}`);

      if (!absPath.startsWith(rootDir)) {
        res.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
        res.end("Forbidden");
        return;
      }

      let finalPath = absPath;
      const stats = await stat(finalPath).catch(() => null);

      if (!stats) {
        res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
        res.end("Not Found");
        return;
      }

      if (stats.isDirectory()) {
        finalPath = join(finalPath, "index.html");
      }

      const fileBuffer = await readFile(finalPath);
      const ext = extname(finalPath).toLowerCase();
      const contentType = MIME_TYPES[ext] || "application/octet-stream";

      res.writeHead(200, {
        "Content-Type": contentType,
        "Cache-Control": "no-store",
      });
      res.end(fileBuffer);
    } catch (error) {
      res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
      res.end(`Server error: ${error.message}`);
    }
  });
}

async function capturePng({ gameDir, outputFile, overwrite, size }) {
  const indexPath = join(gameDir, "index.html");
  const outputPath = join(gameDir, outputFile);

  if (!(await pathExists(indexPath))) {
    throw new Error(`Game page not found: ${indexPath}`);
  }

  if (!overwrite && (await pathExists(outputPath))) {
    throw new Error(`Output file already exists: ${outputPath}. Use --overwrite to replace it.`);
  }

  const routePath = toRoutePath(gameDir);
  const server = createStaticServer(ROOT);

  await new Promise((resolvePromise) => {
    server.listen(0, "127.0.0.1", resolvePromise);
  });

  const address = server.address();
  if (!address || typeof address === "string") {
    throw new Error("Could not start local server");
  }

  const url = `http://127.0.0.1:${address.port}${routePath}/`;

  const browser = await chromium.launch({ headless: true });

  try {
    const context = await browser.newContext({
      viewport: { width: size, height: size },
      deviceScaleFactor: 1,
      colorScheme: "light",
    });

    const page = await context.newPage();

    // Keep page scripts from treating this as a future date and redirecting home.
    await page.addInitScript((futureNowIso) => {
      const RealDate = Date;
      const fixedTime = new RealDate(futureNowIso).valueOf();

      function MockDate(...args) {
        if (this instanceof MockDate) {
          if (args.length === 0) {
            return new RealDate(fixedTime);
          }
          return new RealDate(...args);
        }
        return RealDate(...args);
      }

      MockDate.now = () => fixedTime;
      MockDate.parse = RealDate.parse;
      MockDate.UTC = RealDate.UTC;
      MockDate.prototype = RealDate.prototype;
      Object.setPrototypeOf(MockDate, RealDate);
      globalThis.Date = MockDate;
    }, FUTURE_NOW_ISO);

    await page.goto(url, { waitUntil: "domcontentloaded" });

    if (!page.url().includes(routePath)) {
      throw new Error(`Unexpected redirect while loading ${routePath}. Final URL: ${page.url()}`);
    }

    await page.waitForSelector("four-connect", { timeout: 15000 });
    await page.waitForFunction(() => {
      const game = document.querySelector("four-connect");
      return game?.shadowRoot?.querySelectorAll(".board button").length === 16;
    }, { timeout: 15000 });

    await page.evaluate(async () => {
      document.body.classList.add("export");
      if (document.fonts?.ready) {
        await document.fonts.ready;
      }
    });

    await page.screenshot({
      path: outputPath,
      type: "png",
    });

    await context.close();
    return outputPath;
  } finally {
    await browser.close();
    await new Promise((resolvePromise, rejectPromise) => {
      server.close((error) => {
        if (error) {
          rejectPromise(error);
          return;
        }
        resolvePromise();
      });
    });
  }
}

async function main() {
  try {
    const options = parseArgs(process.argv.slice(2));
    const gameDir = options.date ? gameDirFromDate(options.date) : gameDirFromPath(options.gamePath);
    const gameDate = options.date || dateFromGameDir(gameDir);
    if (!gameDate) {
      throw new Error("Could not infer game date from path. Use --date or a path in games/YYYY/MM/DD format.");
    }
    const outputFile = options.output || `fourconnect-${gameDate}.png`;

    const outputPath = await capturePng({
      gameDir,
      outputFile,
      overwrite: options.overwrite,
      size: options.size,
    });

    console.log(`PNG created: ${outputPath}`);
  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}

await main();
