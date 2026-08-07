/// <reference types="node" />
import { existsSync, readdirSync, readFileSync } from 'fs';
import { access } from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

import {
  validateSlidesManifest,
  type SlideManifestEntry as SlideEntry,
} from '../src/.sdm/core/slidesManifest';
import {
  findOrphanSdmFiles,
  validateSdmEntries,
  type SdmValidationIo,
} from './sdmValidation';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');
const slidesDir = path.join(projectRoot, 'src/pages/slides');
const slidesManifestPath = path.join(
  projectRoot,
  'src/data/slides-manifest.json',
);

type ValidationIssue = {
  message: string;
};

let slides: SlideEntry[] = [];

function relativeToProject(filePath: string): string {
  return path.relative(projectRoot, filePath).replaceAll(path.sep, '/');
}

function formatIssuePath(issuePath: string): string {
  if (issuePath === '') {
    return 'manifest';
  }

  return issuePath
    .slice(1)
    .split('/')
    .map((segment) =>
      segment.replaceAll('~1', '/').replaceAll('~0', '~'),
    )
    .join('.');
}

function getSlideFilenames(): string[] {
  if (!existsSync(slidesDir)) {
    return [];
  }

  return readdirSync(slidesDir).filter((name) => name.endsWith('.tsx'));
}

function validateDuplicatePositions(issues: ValidationIssue[]) {
  const positions = new Map<number, string[]>();
  for (const slide of slides) {
    const list = positions.get(slide.position) ?? [];
    list.push(slide.title);
    positions.set(slide.position, list);
  }

  for (const [position, titles] of positions) {
    if (titles.length > 1) {
      issues.push({
        message: `Duplicate position ${position} found for slides: ${titles.join(', ')}`,
      });
    }
  }
}

function validateDuplicateIds(issues: ValidationIssue[]) {
  const ids = new Map<string, string[]>();
  for (const slide of slides) {
    const list = ids.get(slide.id) ?? [];
    list.push(slide.title);
    ids.set(slide.id, list);
  }

  for (const [id, titles] of ids) {
    if (titles.length > 1) {
      issues.push({
        message: `Duplicate ID ${id} found for slides: ${titles.join(', ')}`,
      });
    }
  }
}

function validateContiguousPositions(issues: ValidationIssue[]) {
  const sorted = [...slides].sort((a, b) => a.position - b.position);
  for (let index = 0; index < sorted.length; index += 1) {
    const expected = index + 1;
    const actual = sorted[index].position;
    if (actual !== expected) {
      issues.push({
        message: `Position gap: expected ${expected}, found ${actual}`,
      });
    }
  }
}

function jsxSlides(): SlideEntry[] {
  return slides.filter((slide) => slide.kind !== 'sdm');
}

function validateFilepaths(issues: ValidationIssue[]) {
  const knownSlideFiles = new Set(getSlideFilenames());

  for (const slide of jsxSlides()) {
    const filename = path.basename(slide.filepath);
    const expectedFilepath = `src/pages/slides/${filename}`;

    if (!filename.endsWith('.tsx')) {
      issues.push({
        message: `Invalid filepath extension for slide "${slide.title}": ${slide.filepath} (must end with .tsx)`,
      });
      continue;
    }

    if (slide.filepath !== expectedFilepath) {
      issues.push({
        message:
          `Invalid filepath for slide "${slide.title}": ${slide.filepath}. ` +
          `Expected ${expectedFilepath} so it resolves in slideLoader.ts.`,
      });
      continue;
    }

    if (!knownSlideFiles.has(filename)) {
      issues.push({
        message: `File not found: ${slide.filepath} (referenced by slide "${slide.title}")`,
      });
    }
  }
}

function validateOrphanedSlideFiles(issues: ValidationIssue[]) {
  const manifestSet = new Set(
    jsxSlides().map((slide) =>
      path.normalize(path.resolve(projectRoot, slide.filepath)),
    ),
  );

  const files = getSlideFilenames().map((name) => path.join(slidesDir, name));

  for (const file of files) {
    if (!manifestSet.has(path.normalize(file))) {
      issues.push({
        message: `Orphaned slide file: ${relativeToProject(file)} (not referenced in manifest)`,
      });
    }
  }
}

function validateSdmSlides(issues: ValidationIssue[]) {
  const io: SdmValidationIo = {
    readFile: (relativePath) => {
      try {
        return readFileSync(path.join(projectRoot, relativePath), 'utf8');
      } catch {
        return null;
      }
    },
    listFiles: (relativeDir) => {
      try {
        return readdirSync(path.join(projectRoot, relativeDir), {
          recursive: true,
          withFileTypes: true,
        })
          .filter((entry) => entry.isFile())
          .map((entry) =>
            relativeToProject(path.join(entry.parentPath, entry.name)).slice(
              `${relativeDir}/`.length,
            ),
          );
      } catch {
        return [];
      }
    },
  };
  const sdmEntries = slides.filter((slide) => slide.kind === 'sdm');
  const messages = [
    ...validateSdmEntries(sdmEntries, io),
    ...findOrphanSdmFiles(slides, io),
  ];
  for (const message of messages) {
    issues.push({ message });
  }
}

async function main() {
  const issues: ValidationIssue[] = [];

  try {
    await access(slidesManifestPath);
  } catch {
    console.error(
      'Slide manifest validation failed (1 issue):\n' +
        '- Missing required manifest file: src/data/slides-manifest.json',
    );
    process.exitCode = 1;
    return;
  }

  let rawManifest: unknown;
  try {
    rawManifest = JSON.parse(
      readFileSync(slidesManifestPath, 'utf8'),
    ) as unknown;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(
      'Slide manifest validation failed (1 issue):\n' +
        `- Failed to parse src/data/slides-manifest.json: ${message}`,
    );
    process.exitCode = 1;
    return;
  }

  const parsedManifest = validateSlidesManifest(rawManifest);
  if (!parsedManifest.ok) {
    console.error(
      `Slide manifest validation failed (${parsedManifest.issues.length} issue(s)):\n`,
    );
    for (const issue of parsedManifest.issues) {
      const issuePath = formatIssuePath(issue.path);
      console.error(`- Invalid manifest at ${issuePath}: ${issue.message}`);
    }
    process.exitCode = 1;
    return;
  }

  slides = parsedManifest.entries;

  validateDuplicatePositions(issues);
  validateDuplicateIds(issues);
  validateContiguousPositions(issues);
  validateFilepaths(issues);
  validateOrphanedSlideFiles(issues);
  validateSdmSlides(issues);

  if (issues.length > 0) {
    console.error(
      `Slide manifest validation failed (${issues.length} issue(s)):\n`,
    );
    for (const issue of issues) {
      console.error(`- ${issue.message}`);
    }
    process.exitCode = 1;
    return;
  }

  console.log(`✓ Slide manifest is valid (${slides.length} slides)`);
}

await main();
