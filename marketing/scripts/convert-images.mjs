#!/usr/bin/env node
/**
 * Build-time image conversion script.
 * Converts PNG/JPG source images in public/images/ to WebP in out/images/.
 *
 * PNG sources  → lossless WebP (logos, icons, crisp UI graphics)
 * JPG sources  → lossy WebP at quality 87 (photos, rich visuals)
 *
 * Excluded from conversion (basename match):
 *   - logo.png         (stays as PNG, used in JSON-LD and favicon contexts)
 *   - opengraph-image.png (OG image stays as PNG; Next.js manages it separately)
 *
 * No-ops gracefully when public/images/ is empty or does not exist.
 * Fails the build (exit 1) if any conversion errors occur.
 *
 * Run: node scripts/convert-images.mjs
 * Called automatically by postbuild script chain.
 */
import sharp from 'sharp'
import { readdir, mkdir } from 'node:fs/promises'
import { join, extname, basename } from 'node:path'
import { existsSync } from 'node:fs'

const SOURCE_DIR = join(process.cwd(), 'public', 'images')
const OUTPUT_DIR = join(process.cwd(), 'out', 'images')

// Belt-and-suspenders exclusion list (basename match).
// These files live outside public/images/ anyway, but guard against accidental copies.
const EXCLUDED = new Set(['logo.png', 'opengraph-image.png'])

const LOSSLESS_EXTENSIONS = new Set(['.png'])
const LOSSY_EXTENSIONS = new Set(['.jpg', '.jpeg'])

/**
 * Recursively find all PNG/JPG/JPEG files in the source directory.
 * Returns empty array if the directory does not exist.
 */
async function getImageFiles(dir) {
  if (!existsSync(dir)) return []

  const entries = await readdir(dir, { withFileTypes: true, recursive: true })

  return entries
    .filter(e => e.isFile())
    .map(e => join(e.parentPath ?? e.path, e.name))
    .filter(f => {
      const ext = extname(f).toLowerCase()
      return (LOSSLESS_EXTENSIONS.has(ext) || LOSSY_EXTENSIONS.has(ext)) &&
        !EXCLUDED.has(basename(f))
    })
}

/**
 * Convert a single source image to WebP in the output directory.
 * Preserves subdirectory structure from public/images/ into out/images/.
 */
async function convertToWebP(sourcePath) {
  const ext = extname(sourcePath).toLowerCase()
  const rel = sourcePath.slice(SOURCE_DIR.length + 1)
  const outPath = join(OUTPUT_DIR, rel.replace(/\.(png|jpe?g)$/i, '.webp'))
  const outDir = join(outPath, '..')

  await mkdir(outDir, { recursive: true })

  const isLossless = LOSSLESS_EXTENSIONS.has(ext)

  await sharp(sourcePath)
    .webp(
      isLossless
        ? { lossless: true }
        : { quality: 87, effort: 4 }
    )
    .toFile(outPath)

  return outPath
}

// --- Main ---

const files = await getImageFiles(SOURCE_DIR)

if (files.length === 0) {
  console.log('Image pipeline: no images in public/images/ — skipping')
  process.exit(0)
}

console.log(`Image pipeline: converting ${files.length} image(s) to WebP...`)

let converted = 0
let failed = 0

for (const file of files) {
  try {
    const out = await convertToWebP(file)
    console.log(`  OK  ${basename(file)} -> ${basename(out)}`)
    converted++
  } catch (err) {
    console.error(`  ERR ${basename(file)}: ${err.message}`)
    failed++
  }
}

if (failed > 0) {
  console.error(`\nImage pipeline FAILED — ${failed} error(s)`)
  process.exit(1)
}

console.log(`Image pipeline: ${converted} image(s) converted successfully`)
