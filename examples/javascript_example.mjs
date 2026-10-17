// Minimal consumer example. Run with: node examples/javascript_example.mjs
// Uses the local file so it works offline; swap in the raw GitHub URL to read
// the published dataset.

import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const specs = JSON.parse(await readFile(join(here, '..', 'data', 'specs.json'), 'utf8'));

const find = (code, type = 'passport') =>
  specs.find((s) => s.countryCode === code.toUpperCase() && s.documentType === type);

const targetPixels = (spec, dpi = 300) =>
  spec.unit === 'px'
    ? [spec.pixelWidth, spec.pixelHeight]
    : [Math.round((spec.widthMm / 25.4) * dpi), Math.round((spec.heightMm / 25.4) * dpi)];

for (const code of ['JP', 'US', 'GB', 'NL']) {
  const spec = find(code);
  if (!spec) continue;
  const [w, h] = targetPixels(spec, spec.dpi);
  const size =
    spec.unit === 'px'
      ? `${spec.pixelWidth}x${spec.pixelHeight} px`
      : `${spec.widthMm}x${spec.heightMm} mm`;
  const head = spec.headMinMm ? `${spec.headMinMm}-${spec.headMaxMm} mm` : 'not verified';
  console.log(
    `${spec.countryName.padEnd(18)} ${size.padEnd(14)} ` +
      `${w}x${h} px @${spec.dpi}dpi  bg ${spec.backgroundColor}  head ${head}`
  );
}

// Group by document type, ignoring records whose size is still under review.
const counts = specs
  .filter((s) => !s.needsReview)
  .reduce((acc, s) => ({ ...acc, [s.documentType]: (acc[s.documentType] ?? 0) + 1 }), {});

console.log('\nverified records by type:', counts);
