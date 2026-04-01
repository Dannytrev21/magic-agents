import { readFileSync, statSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gzipSync } from 'node:zlib';

const __dirname = dirname(fileURLToPath(import.meta.url));
const uiRoot = resolve(__dirname, '..');
const outputRoot = resolve(uiRoot, '../static/ui');
const manifestPath = resolve(outputRoot, '.vite/manifest.json');
const budgetsPath = resolve(uiRoot, 'config/bundle-budgets.json');

const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
const budgetConfig = JSON.parse(readFileSync(budgetsPath, 'utf8'));

const failures = [];
const reportLines = [];

for (const assetBudget of budgetConfig.assets) {
  const manifestEntry = manifest[assetBudget.manifestKey];

  if (!manifestEntry) {
    failures.push(`Missing manifest entry for ${assetBudget.manifestKey}`);
    continue;
  }

  const assetPath = resolveAssetPath(manifestEntry, assetBudget.source);

  if (!assetPath) {
    failures.push(`Missing asset path ${assetBudget.source} for ${assetBudget.manifestKey}`);
    continue;
  }

  const absoluteAssetPath = resolve(outputRoot, assetPath);
  const rawBytes = statSync(absoluteAssetPath).size;
  const gzipBytes = gzipSync(readFileSync(absoluteAssetPath)).length;

  reportLines.push(
    `${assetBudget.label}: ${formatBytes(rawBytes)} raw / ${formatBytes(gzipBytes)} gzip`,
  );

  if (rawBytes > assetBudget.maxBytes) {
    failures.push(
      `${assetBudget.label} exceeded raw budget (${formatBytes(rawBytes)} > ${formatBytes(assetBudget.maxBytes)})`,
    );
  }

  if (gzipBytes > assetBudget.maxGzipBytes) {
    failures.push(
      `${assetBudget.label} exceeded gzip budget (${formatBytes(gzipBytes)} > ${formatBytes(assetBudget.maxGzipBytes)})`,
    );
  }
}

for (const line of reportLines) {
  console.log(line);
}

if (failures.length) {
  for (const failure of failures) {
    console.error(failure);
  }
  process.exit(1);
}

function resolveAssetPath(manifestEntry, source) {
  if (source === 'file') {
    return manifestEntry.file ?? null;
  }

  if (source.startsWith('css.')) {
    const index = Number(source.split('.')[1]);
    return Number.isInteger(index) ? manifestEntry.css?.[index] ?? null : null;
  }

  return null;
}

function formatBytes(value) {
  return `${(value / 1024).toFixed(2)} kB`;
}
