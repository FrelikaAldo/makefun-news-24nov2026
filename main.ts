// main.ts — the entry for makefun-news-24nov2026 (Node 22, standard library only).
//
// The page is already drawn: entry.png beside this file is the front page of
// Tuesday 24 November 2026. This program is what the grader runs. Before it copies
// anything it checks that the image is one the gate will accept, so a broken or
// oversized file fails here with a sentence that says what is wrong, instead of
// going before the judge as a rejected entry.
//
// Determinism: nothing here reads the clock, the network, or any environment beyond
// the output directory, and the bytes are copied verbatim. Two runs write the same
// file, which is what the harness requires.
//
//   mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts

import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const MAX_BYTES = 1_048_576; // 1 MiB, the gate's byte cap
const MAX_SIDE = 1024; // the gate's pixel cap, either side

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, 'entry.png');
const outputDir = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';
const destination = join(outputDir, 'entry.png');

/** Stop the run with a reason the reader can act on. */
function refuse(reason: string): never {
  process.stderr.write(`entry.png refused: ${reason}\n`);
  process.exit(1);
}

/** Bytes as hex, so a bad header can be named rather than described. */
function hex(bytes: Buffer): string {
  return [...bytes].map((b) => b.toString(16).padStart(2, '0')).join(' ');
}

/** Read the image, or refuse if it is missing or unreadable. */
async function readImage(path: string): Promise<Buffer> {
  try {
    return await readFile(path);
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code ?? 'unknown error';
    refuse(`cannot read ${path} (${code})`);
  }
}

/** Check the header the gate checks, and return the dimensions it declares. */
function inspect(png: Buffer): { width: number; height: number } {
  const found = png.subarray(0, PNG_SIGNATURE.length);

  if (png.length === 0) {
    refuse(`the file is empty, so it starts with no PNG signature at all`);
  }

  if (found.length < PNG_SIGNATURE.length || !found.equals(PNG_SIGNATURE)) {
    refuse(
      `not a PNG: a PNG starts with the 8-byte signature 89 50 4e 47 0d 0a 1a 0a, ` +
        `and this file starts with ${hex(found)}`,
    );
  }

  if (png.length < 24) {
    refuse(`the file is only ${png.length} bytes, too short to hold an IHDR chunk`);
  }

  const chunkType = png.subarray(12, 16).toString('latin1');
  if (chunkType !== 'IHDR') {
    refuse(`the first chunk is ${hex(png.subarray(12, 16))} ("${chunkType}"), not IHDR`);
  }

  // IHDR carries the width and height as big-endian uint32 at bytes 16..24.
  const width = png.readUInt32BE(16);
  const height = png.readUInt32BE(20);

  if (width === 0 || height === 0) {
    refuse(`the header declares ${width}x${height}, and a PNG has to have both sides above zero`);
  }

  if (width > MAX_SIDE || height > MAX_SIDE) {
    refuse(
      `the header declares ${width}x${height}, and the gate takes at most ` +
        `${MAX_SIDE}x${MAX_SIDE}, so one or both sides is too large`,
    );
  }

  return { width, height };
}

const png = await readImage(source);
const { width, height } = inspect(png);

if (png.length > MAX_BYTES) {
  const over = png.length - MAX_BYTES;
  refuse(
    `the file is ${png.length} bytes and the cap is ${MAX_BYTES} bytes (1 MiB), ` +
      `${over} bytes over`,
  );
}

await mkdir(outputDir, { recursive: true });
await writeFile(destination, png);

process.stdout.write(`${destination} ${width}x${height} ${png.length} bytes\n`);