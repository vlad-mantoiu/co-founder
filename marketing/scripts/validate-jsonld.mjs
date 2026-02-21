#!/usr/bin/env node
/**
 * Build-time JSON-LD validation script.
 * Reads built HTML from out/ and validates JSON-LD schemas
 * against Google Rich Results required fields.
 *
 * Run: node scripts/validate-jsonld.mjs
 * Called automatically by postbuild script.
 */
import { readFileSync, existsSync } from 'node:fs'
import { join } from 'node:path'

const OUT_DIR = join(process.cwd(), 'out')
const errors = []
const warnings = []
let totalSchemas = 0

/**
 * Extract JSON-LD blocks from an HTML file
 */
function extractSchemas(htmlPath) {
  if (!existsSync(htmlPath)) {
    errors.push(`File not found: ${htmlPath}`)
    return []
  }
  const html = readFileSync(htmlPath, 'utf8')
  const regex = /<script type="application\/ld\+json">([\s\S]*?)<\/script>/g
  const schemas = []
  let match
  while ((match = regex.exec(html)) !== null) {
    try {
      schemas.push(JSON.parse(match[1]))
    } catch (e) {
      errors.push(`Invalid JSON-LD in ${htmlPath}: ${e.message}`)
    }
  }
  return schemas
}

/**
 * Validate Organization schema (Google Rich Results requirements)
 */
function validateOrganization(schema, file) {
  if (!schema.name) errors.push(`${file}: Organization missing 'name'`)
  if (!schema.url) errors.push(`${file}: Organization missing 'url'`)
  if (!schema.logo) errors.push(`${file}: Organization missing 'logo' (required for Logo rich result)`)
  if (schema.sameAs && Array.isArray(schema.sameAs) && schema.sameAs.length === 0) {
    warnings.push(`${file}: Organization has empty 'sameAs' array — remove or populate`)
  }
}

/**
 * Validate WebSite schema (Google Rich Results requirements)
 */
function validateWebSite(schema, file) {
  if (!schema.name) errors.push(`${file}: WebSite missing 'name'`)
  if (!schema.url) errors.push(`${file}: WebSite missing 'url'`)
}

/**
 * Validate FAQPage schema (Google Rich Results requirements)
 */
function validateFAQPage(schema, file) {
  if (!schema.mainEntity) {
    errors.push(`${file}: FAQPage missing 'mainEntity' (required)`)
    return
  }
  if (!Array.isArray(schema.mainEntity) || schema.mainEntity.length === 0) {
    errors.push(`${file}: FAQPage 'mainEntity' must be a non-empty array`)
    return
  }
  for (let i = 0; i < schema.mainEntity.length; i++) {
    const q = schema.mainEntity[i]
    if (q['@type'] !== 'Question') {
      errors.push(`${file}: FAQPage mainEntity[${i}] must have @type 'Question'`)
    }
    if (!q.name) {
      errors.push(`${file}: FAQPage mainEntity[${i}] missing 'name' (the question text)`)
    }
    if (!q.acceptedAnswer) {
      errors.push(`${file}: FAQPage mainEntity[${i}] missing 'acceptedAnswer'`)
    } else {
      if (q.acceptedAnswer['@type'] !== 'Answer') {
        errors.push(`${file}: FAQPage mainEntity[${i}].acceptedAnswer must have @type 'Answer'`)
      }
      if (!q.acceptedAnswer.text) {
        errors.push(`${file}: FAQPage mainEntity[${i}].acceptedAnswer missing 'text'`)
      }
    }
  }
}

/**
 * Validate SoftwareApplication schema (Google Rich Results requirements)
 */
function validateSoftwareApplication(schema, file) {
  if (!schema.name) errors.push(`${file}: SoftwareApplication missing 'name'`)
  if (!schema.offers) {
    errors.push(`${file}: SoftwareApplication missing 'offers' (required)`)
  } else {
    if (schema.offers.price === undefined) {
      errors.push(`${file}: SoftwareApplication missing 'offers.price' (required)`)
    }
    if (!schema.offers.priceCurrency) {
      errors.push(`${file}: SoftwareApplication missing 'offers.priceCurrency' (required)`)
    }
  }
  if (!schema.aggregateRating && !schema.review) {
    warnings.push(`${file}: SoftwareApplication has no aggregateRating or review — star ratings will not show in search results (acceptable for new products)`)
  }
}

// Pages to validate
// Homepage has Organization + WebSite
// /cofounder has SoftwareApplication + FAQPage
// /pricing has FAQPage
const pagesToValidate = [
  { path: 'index.html', expectedTypes: ['Organization', 'WebSite'] },
  { path: 'cofounder/index.html', expectedTypes: ['SoftwareApplication', 'FAQPage'] },
  { path: 'pricing/index.html', expectedTypes: ['FAQPage'] },
]

console.log('Validating JSON-LD schemas...\n')

for (const page of pagesToValidate) {
  const htmlPath = join(OUT_DIR, page.path)
  const schemas = extractSchemas(htmlPath)

  if (schemas.length === 0 && page.expectedTypes.length > 0) {
    errors.push(`${page.path}: No JSON-LD schemas found (expected: ${page.expectedTypes.join(', ')})`)
    continue
  }

  for (const schema of schemas) {
    totalSchemas++
    const type = schema['@type']

    if (!schema['@context'] || !schema['@context'].includes('schema.org')) {
      errors.push(`${page.path}: Schema missing '@context' with schema.org`)
    }

    switch (type) {
      case 'Organization':
        validateOrganization(schema, page.path)
        break
      case 'WebSite':
        validateWebSite(schema, page.path)
        break
      case 'SoftwareApplication':
        validateSoftwareApplication(schema, page.path)
        break
      case 'FAQPage':
        validateFAQPage(schema, page.path)
        break
      default:
        warnings.push(`${page.path}: Unknown schema type '${type}'`)
    }
  }

  // Check expected types are present
  const foundTypes = schemas.map(s => s['@type'])
  for (const expected of page.expectedTypes) {
    if (!foundTypes.includes(expected)) {
      errors.push(`${page.path}: Missing expected schema type '${expected}'`)
    }
  }

  console.log(`  ${page.path}: ${schemas.length} schema(s) — ${schemas.map(s => s['@type']).join(', ')}`)
}

console.log('')

if (warnings.length > 0) {
  console.warn('Warnings:')
  warnings.forEach(w => console.warn(`  ! ${w}`))
  console.log('')
}

if (errors.length > 0) {
  console.error('Errors:')
  errors.forEach(e => console.error(`  x ${e}`))
  console.log('')
  console.error(`JSON-LD validation FAILED — ${errors.length} error(s)`)
  process.exit(1)
}

console.log(`JSON-LD validation passed — ${totalSchemas} schema(s) validated across ${pagesToValidate.length} page(s)`)
