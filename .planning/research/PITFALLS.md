# Pitfalls Research

**Domain:** Premium loading UX, performance optimization, SEO, and GEO — added to existing Next.js static export on CloudFront + S3
**Researched:** 2026-02-20
**Confidence:** HIGH — all pitfalls verified against codebase inspection, official Next.js docs, AWS documentation, and community post-mortems

> **Scope:** This is a milestone-specific addendum. It covers integration pitfalls for ADDING premium loading UX, performance optimization, SEO, and GEO to the existing `marketing/` static export site served via CloudFront + S3. The existing setup uses `output: "export"`, `trailingSlash: true`, `images: { unoptimized: true }`, a CloudFront function for clean URL rewriting, and `ResponseHeadersPolicy.SECURITY_HEADERS`.

---

## Critical Pitfalls

### Pitfall 1: SECURITY_HEADERS Managed Policy Blocks Clerk Auth and Third-Party Scripts

**What goes wrong:**
The CDK stack applies `cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS` to the default behavior. This managed policy includes a `Content-Security-Policy` header that uses restrictive defaults for `frame-src`, `script-src`, and `connect-src`. Clerk requires `frame-src` to include `https://challenges.cloudflare.com` and the Clerk FAPI domain. It also requires `script-src` to allow the Clerk FAPI host and `style-src` to allow `'unsafe-inline'`. Any analytics, font loading from Google Fonts, or third-party performance scripts (e.g., `gtag.js`) added during this milestone will be blocked by a strict CSP applied via the managed policy. The managed policy does not expose per-directive configuration — you cannot extend it without replacing it entirely.

**Why it happens:**
The AWS managed `SECURITY_HEADERS` policy is designed for simple static sites with no third-party dependencies. The marketing site already has `space-grotesk` loading from Google Fonts in the root layout. Adding performance monitoring scripts, analytics, or structured data verification tools (e.g., Google's Rich Results Test bot) can be silently blocked by a CSP that isn't visible in the codebase — it lives in the AWS console, not in source code.

**How to avoid:**
- Replace `ResponseHeadersPolicy.SECURITY_HEADERS` with a custom `cloudfront.ResponseHeadersPolicy` that explicitly lists allowed sources per directive
- Required Clerk allowlist in CSP: `script-src: 'self' <clerk-fapi-domain>; style-src: 'self' 'unsafe-inline'; frame-src: 'self' https://challenges.cloudflare.com; connect-src: 'self' <clerk-fapi-domain>; img-src: 'self' data: https://img.clerk.com; worker-src: 'self' blob:`
- For Google Fonts (Space Grotesk in the marketing layout): add `style-src: https://fonts.googleapis.com` and `font-src: https://fonts.gstatic.com` — unless this milestone self-hosts fonts via `next/font`, in which case these can be omitted
- Define the policy in CDK (not the AWS console) so it is version-controlled and visible
- Test CSP by opening browser DevTools → Console after deploy; blocked resources appear immediately as CSP violation errors

**Warning signs:**
- Clerk sign-in component renders blank or shows a Cloudflare challenge iframe that never loads
- Google Fonts fail to load (FOUT in Lighthouse, visible in DevTools Network as CSP-blocked request)
- DevTools Console shows `Refused to load script` or `Refused to connect` with `Content-Security-Policy` as the reason
- Any structured data injection script or analytics tag is silently blocked with no visible error to the user

**Phase to address:** Phase 1 (Security headers audit) — must be the first change in the milestone, before any loading UX or SEO scripts are added; otherwise every test is against a broken baseline

---

### Pitfall 2: Splash Screen / Branded Loader Causes FOUC and Hydration Race

**What goes wrong:**
A branded splash screen that fades out after N milliseconds works perfectly in local dev but causes a Flash of Unstyled Content (FOUC) or visible layout jump in production. The pattern `useState(true)` for `showSplash` initialized server-side produces `true` on the static HTML, then the client hydrates, `useEffect` runs after ~100ms, and the splash disappears — but if fonts haven't loaded yet, the content underneath the splash flashes unstyled for a frame before font-swap completes. The reverse problem also occurs: if the splash is initially `false` server-side and `true` client-side (to "detect" if JS is running), React throws a hydration mismatch and renders the splash only on the second paint, causing a double-flash.

**Why it happens:**
Static export pre-renders all HTML server-side. Any `useState` initial value that differs between server render and client first paint produces either a hydration error or a visible content flash. Splash screens read `window`, `document.fonts`, or `localStorage` — none of which exist during static pre-rendering. Wrapping in `useEffect` alone doesn't prevent the initial server-rendered HTML from being visible for the ~16ms between HTML parse and React hydration.

**How to avoid:**
- Initialize `showSplash` to `true` in `useState` and set it to `false` in `useEffect` — this is the correct pattern for static export; the server renders the splash (which is correct), and the client hides it after JS runs
- Ensure the splash component is a `"use client"` component so it never attempts SSR of browser APIs
- Use CSS `opacity` transition (not `display: none`) so the transition is smooth and composited by the GPU — no layout shifts
- Load fonts with `next/font` in the marketing `layout.tsx` before the splash renders; fonts are inlined at build time so Space Grotesk is available on first paint without a network request
- Do NOT use `document.fonts.ready` as a splash dismissal trigger — it fires inconsistently on CloudFront edge caches where the HTML arrives without font preloads in some regions

**Warning signs:**
- React DevTools shows hydration error warning for the splash component
- Lighthouse CLS score > 0.05 specifically on the marketing home page
- Space Grotesk font loads after the splash fades, causing a FOUT visible in the hero headline
- WebPageTest filmstrip shows a blank white frame between splash fade and content reveal

**Phase to address:** Phase 2 (Loading UX) — address before splash screen code is written; the initialization pattern must be decided upfront

---

### Pitfall 3: `loading.tsx` File Convention Does Not Work with `output: "export"`

**What goes wrong:**
Next.js App Router's `loading.tsx` file convention uses React Suspense with server-side streaming to show skeleton screens while route segments load. With `output: "export"`, there is no runtime server and no streaming. `loading.tsx` files are silently ignored — Next.js does not error on them, it just never uses them. Developers write skeleton screens in `loading.tsx`, test in dev mode (where the server is running), see them work, deploy to S3, and discover they never appear. The skeleton only works in dev because dev mode uses a server even when `output: "export"` is set.

**Why it happens:**
The Next.js docs for `loading.tsx` do not prominently warn about static export incompatibility. The file is legal to create; it simply has no effect in a static export context. Dev mode (`next dev`) always runs a server regardless of the `output` config.

**How to avoid:**
- Do not use `loading.tsx` for skeleton screens in the marketing site
- Implement skeletons as client-side `useState`-based loading states within the page component itself: `const [loaded, setLoaded] = useState(false)` + `useEffect(() => setLoaded(true), [])` — render the skeleton JSX when `!loaded`
- For the progress bar (NProgress-style), use `next-nprogress-bar` which wraps Next.js `<Link>` and `router.push` with manual `NProgress.start()` calls — this is required because App Router does not expose router events for NProgress to hook into automatically
- Test skeleton screens with `next build && npx serve out` (serving the static export) — not `next dev`

**Warning signs:**
- Skeleton screens appear in dev (`npm run dev`) but never in production
- `loading.tsx` files exist in `app/` directory of the marketing site
- Build output (`out/`) contains no skeleton-related HTML — only the fully rendered page
- `next build` completes without warnings about `loading.tsx`

**Phase to address:** Phase 2 (Loading UX) — the skeleton implementation approach must be established before writing any skeleton code

---

### Pitfall 4: CloudFront Caches Stale HTML After Deploy — Visitors See Old Content for 5 Minutes

**What goes wrong:**
The existing CDK stack sets `htmlCachePolicy` to `defaultTtl: Duration.minutes(5)`. After a deploy, CloudFront edge nodes continue serving the old `index.html` and page HTML for up to 5 minutes to cached visitors. For a marketing site, this means a visitor who lands during that window sees the old splash screen, old meta tags, or old structured data. If a deploy fixes a broken OG image URL, search engine crawlers that re-visit within 5 minutes receive the broken version again. More critically: if a new `_next/static/` hash is deployed alongside the HTML update, users with cached HTML may request new JS chunk filenames but receive a 404 from S3 (the new chunks exist, but the cached HTML references a hash that no longer exists or the old HTML references chunks that were deleted).

**Why it happens:**
The 5-minute TTL was set as a "short but not zero" compromise. A CloudFront invalidation (`/*`) is required after every deploy to flush the HTML cache. If the deploy script uploads to S3 but does not invalidate, the stale HTML/chunk mismatch window opens.

**How to avoid:**
- Every deploy must run `aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"` as the final step, after S3 sync completes
- The `/*` wildcard path counts as ONE invalidation path (not one per file), so cost is $0 for the first 1,000/month — for a marketing site this is always free
- Use the CDK output `CoFounderMarketingDistributionId` to parameterize the invalidation command
- Upload order matters: upload `_next/static/` (hashed assets) FIRST, then upload HTML files — this ensures that if a user loads the new HTML, the new chunks already exist in S3; the reverse order creates a window where new HTML references non-existent chunks
- Consider setting the HTML TTL to `Duration.seconds(0)` (with `minTtl: 0`) plus an `s-maxage: 0, must-revalidate` Cache-Control header to force CloudFront to always check S3; this removes the 5-minute window entirely at the cost of higher S3 origin requests (still cheap at marketing site traffic volumes)

**Warning signs:**
- After a deploy, visiting the site in a private browser window shows the old version for several minutes
- JS console shows `Failed to load resource: 404` for a `/_next/static/chunks/...` file immediately after a deploy
- The deploy script ends without a CloudFront invalidation command
- Lighthouse run immediately post-deploy shows the old page title / OG tags

**Phase to address:** Phase 3 (Performance optimization) and the CI/CD deploy step — invalidation must be wired into the deploy script before the first SEO/OG metadata changes ship

---

### Pitfall 5: Sitemap Generation Errors with `output: "export"` and `trailingSlash: true`

**What goes wrong:**
Next.js App Router's built-in `sitemap.ts` route handler (`/app/sitemap.ts`) requires `export const dynamic = 'force-static'` when used with `output: "export"`. Without this export, the build fails with: `Error: Page "/sitemap.xml" is missing "generateStaticParams()" function`. Additionally, when `trailingSlash: true` is set, there is a known bug (Next.js issue #68215) where routes generated by `sitemap.ts` may not add the `/index.html` suffix correctly, producing sitemap URLs that don't match the actual S3 paths. The CloudFront function then rewrites those URLs to `/index.html` at the edge, but Google's sitemap parser sees the trailing-slash version and Google Search Console may report URL discrepancies.

**Why it happens:**
The sitemap route handler was designed for server-rendered Next.js. The `output: "export"` mode forces every route to be a static file; the sitemap handler must be explicitly marked as static-only. The `trailingSlash` interaction is a Next.js bug that has been open since v14.2.

**How to avoid:**
- Add `export const dynamic = 'force-static'` to `marketing/src/app/sitemap.ts` or use `next-sitemap` as a post-build script (runs after `next build`, reads the `out/` directory, generates `sitemap.xml` and `robots.txt` as plain files)
- `next-sitemap` is the recommended approach for static export because it bypasses the App Router route handler entirely and generates files that are guaranteed to match the actual output structure
- Configure `next-sitemap.config.js` with `trailingSlash: true` to match the CloudFront URL rewriting so sitemap URLs exactly match what CloudFront serves (include `/`, not `.html`)
- Verify sitemap URLs by fetching `https://getinsourced.ai/sitemap.xml` after deploy and checking that each URL returns a 200 (not a redirect or 404)
- Submit the sitemap URL to Google Search Console and Bing Webmaster Tools after the first deploy that includes it

**Warning signs:**
- `next build` fails with `Error: Page "/sitemap.xml" is missing "generateStaticParams()"`
- `sitemap.xml` exists in `out/` but its URLs use `.html` extensions or mismatched trailing slashes
- Google Search Console reports "Submitted URL seems to be a Soft 404" for sitemap URLs
- `curl https://getinsourced.ai/sitemap.xml` returns 403 or 404 (file not uploaded to S3 correctly)

**Phase to address:** Phase 4 (SEO) — implement `next-sitemap` during the SEO phase; never use the App Router sitemap handler for static export

---

### Pitfall 6: OG Image `metadataBase` Missing — Social Previews Show No Image

**What goes wrong:**
The marketing site's `layout.tsx` defines `openGraph.title` and `openGraph.description` but does not define `openGraph.images` or `metadataBase`. When sharing `https://getinsourced.ai/cofounder` on LinkedIn, Twitter/X, or Slack, the unfurl preview shows no image — just the title and description. Search engines may also treat a page without OG image as lower quality for rich preview snippets. The root cause is that any relative path used for `og:image` (e.g., `/og-image.png`) is not resolved to an absolute URL without `metadataBase`, producing a `<meta property="og:image" content="/og-image.png">` tag that social scrapers cannot follow.

**Why it happens:**
On Vercel, the `VERCEL_URL` environment variable automatically provides a `metadataBase` fallback. On a CloudFront + S3 static export, there is no such environment variable — `metadataBase` must be set explicitly. The Next.js docs note this but the build does not fail or warn when `metadataBase` is absent.

**How to avoid:**
- Add `metadataBase: new URL('https://getinsourced.ai')` to the root `layout.tsx` metadata export in the marketing site
- Store the OG image as a static file in `marketing/public/og-image.png` (1200×630px, <1MB, PNG or JPG)
- Reference it with `openGraph: { images: [{ url: '/og-image.png', width: 1200, height: 630 }] }` — Next.js will combine `metadataBase` with the relative path to produce `https://getinsourced.ai/og-image.png` in the rendered HTML
- Verify with the Facebook Sharing Debugger (`developers.facebook.com/tools/debug/`), LinkedIn Post Inspector, and Twitter Card Validator before considering the feature complete
- Add `robots.txt` `Allow: /og-image.png` to prevent accidental blocking by a restrictive robots file

**Warning signs:**
- Social sharing produces a blank card with no image
- `curl -s https://getinsourced.ai/ | grep og:image` returns a relative path (`/og-image.png`) without a domain prefix
- LinkedIn Post Inspector shows "og:image not found" or "og:image size too small"
- No `metadataBase` in `marketing/src/app/layout.tsx`

**Phase to address:** Phase 4 (SEO) — implement alongside all other meta tag work; OG image is a prerequisite for GEO citation quality

---

### Pitfall 7: Image CLS from `unoptimized: true` — Missing `width`/`height` Props

**What goes wrong:**
The marketing site uses `images: { unoptimized: true }` in `next.config.ts`, which disables Next.js image optimization. This is required for static export. However, developers often interpret "unoptimized" as meaning they don't need to worry about image dimensions — they use `<Image src="/hero.png" fill />` or `<img>` tags without explicit dimensions. Without `width` and `height`, the browser cannot reserve space for the image before it loads, causing a Cumulative Layout Shift (CLS) when the image arrives. CLS above 0.1 is a Core Web Vitals failure that directly impacts SEO ranking. The current marketing site uses CSS background images for decorative gradients (safe), but adding hero screenshots or product mockup images without dimensions is the trap.

**Why it happens:**
`unoptimized: true` disables server-side resizing and format conversion, but `next/image` still provides layout-shift prevention if `width` and `height` are supplied. The distinction between "optimization" (format conversion, compression) and "layout reservation" (aspect ratio calculation) is not obvious from the config name.

**How to avoid:**
- Always provide explicit `width` and `height` on every `<Image>` component, even with `unoptimized: true`
- For responsive images that fill a container, use `fill` prop with a sized parent container (`position: relative; aspect-ratio: 16/9`) — this prevents CLS because the container size is known
- For the chat UI mockup in the hero section, use `width={600} height={420}` (or the actual rendered dimensions) to let the browser reserve space
- Run Lighthouse CLS audit locally before deploying any new images: `npx lighthouse https://getinsourced.ai --only-categories=performance`
- Consider `next-image-export-optimizer` if WebP conversion at build time is needed — it runs a post-build optimization step compatible with `output: "export"`

**Warning signs:**
- Lighthouse CLS score above 0.05 on any marketing page
- WebPageTest filmstrip shows content "jumping" as images load
- `<Image>` without `width` and `height` and without `fill` — Next.js will log a warning but not fail the build
- Decorative gradient divs replaced with real product screenshots during the UX refresh

**Phase to address:** Phase 2 (Loading UX) when images are added; Phase 3 (Performance) verification during Lighthouse audits

---

### Pitfall 8: GEO Structured Data Not in `<head>` — JSON-LD Injected Client-Side Only

**What goes wrong:**
AI crawlers (Perplexity, ChatGPT SearchGPT, Google Gemini) do not execute JavaScript when scraping pages. If JSON-LD structured data is injected via a `useEffect` or a client-only component, the `<script type="application/ld+json">` tag is absent from the static HTML and the AI crawler never sees it. The site appears to have no structured data in AI engine indices. This is the single most common GEO mistake: developers test with a browser (where JS runs) and see the structured data in DevTools, but crawlers receive only the pre-rendered HTML without JS execution.

**Why it happens:**
In Next.js App Router, adding JSON-LD in a Server Component renders it in the static HTML automatically. But if a developer wraps the JSON-LD script in a `"use client"` component (e.g., to make it dynamic based on props), it only appears after React hydrates, which AI crawlers never wait for. The marketing site's components are already `"use client"` for Framer Motion animations — it's easy to accidentally include the JSON-LD in a client component.

**How to avoid:**
- Add JSON-LD structured data in Server Components only — in `layout.tsx` or `page.tsx` at the marketing site level (these are currently Server Components since no `"use client"` directive is at the top)
- Use Next.js's built-in JSON-LD support: add a `<script type="application/ld+json">` tag directly in the layout's `<head>` using the `metadata` export or inline in the JSX
- Verify structured data is in the static HTML: `curl https://getinsourced.ai/ | grep -A 20 'application/ld+json'` — if no output, the data is client-only
- Required schemas for AI citation: `Organization`, `WebSite`, `SoftwareApplication` (for Co-Founder.ai), `FAQPage` for common "what is" questions
- Test with Google's Rich Results Test (`search.google.com/test/rich-results`) and with `curl -A "Googlebot"` to simulate crawler behavior

**Warning signs:**
- Google Rich Results Test shows "No structured data detected" despite JSON-LD existing in the component
- `curl https://getinsourced.ai/` output contains no `application/ld+json` script tag
- JSON-LD is inside a component that has `"use client"` at the top
- AI engines (ChatGPT, Perplexity) don't cite the site even for queries where the content is directly relevant

**Phase to address:** Phase 5 (GEO) — structured data must be in Server Components from the start; retrofitting it after the fact is risky if components have already been made client-only

---

### Pitfall 9: `robots.txt` Not Uploaded to S3 or Cached Too Aggressively

**What goes wrong:**
The existing CloudFront setup uses `trailingSlash: true` and the CloudFront function rewrites clean URLs to `/index.html`. `robots.txt` is a plain text file at the root — it does NOT go through the URL rewriter because it contains a dot extension (the rewriter skips paths with extensions). However, if `robots.txt` is uploaded to S3 with no `Cache-Control` header, CloudFront applies the `htmlCachePolicy` (5-minute TTL). If `robots.txt` is accidentally excluded from the S3 sync (common when syncing only the `out/_next/` directory or using glob patterns that exclude root files), AI crawlers receive a 403/404 and apply conservative defaults — some crawlers treat a missing `robots.txt` as "no crawling allowed."

Additionally, the `output: "export"` build does NOT generate `robots.txt` automatically. It must be either: (a) placed in `marketing/public/robots.txt` as a static file, or (b) generated via `next-sitemap` post-build.

**Why it happens:**
The `next build` output only generates what is defined in the app. `robots.txt` in `public/` is copied to `out/` — but if the deploy script uses `aws s3 sync out/ s3://getinsourced-marketing/ --exclude "*" --include "_next/*"` or a similar partial sync, `robots.txt` and `sitemap.xml` at the root are excluded.

**How to avoid:**
- Sync the entire `out/` directory to S3: `aws s3 sync out/ s3://getinsourced-marketing/ --delete`
- Create `marketing/public/robots.txt` explicitly with `User-agent: *\nAllow: /\nSitemap: https://getinsourced.ai/sitemap.xml`
- Add `Cache-Control: public, max-age=86400` as object metadata on `robots.txt` and `sitemap.xml` during S3 upload — these files change infrequently and 24-hour caching is appropriate
- Verify post-deploy: `curl -I https://getinsourced.ai/robots.txt` should return `200 OK`, not `403` or `404`
- Ensure `robots.txt` does NOT accidentally disallow `/` for protected/app routes (the marketing site only — the app at `cofounder.getinsourced.ai` has separate routing and robots logic)

**Warning signs:**
- `curl https://getinsourced.ai/robots.txt` returns 403 (OAC S3 access denied on a non-existent key) or 404 (mapped to `/404.html` by CloudFront error responses)
- Google Search Console shows "robots.txt unreachable" warning
- AI crawlers cite competitor sites for "AI technical co-founder" queries despite the marketing site having relevant content
- Sitemap URL is not referenced in `robots.txt`

**Phase to address:** Phase 4 (SEO) — `robots.txt` is a prerequisite for sitemap discovery and indexing

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `ResponseHeadersPolicy.SECURITY_HEADERS` with third-party scripts | Works out of the box | Silently blocks Clerk, analytics, Google Fonts; invisible CSP errors | **Never for a site with third-party dependencies** — replace with custom policy immediately |
| Splash screen `useState(false)` that becomes `true` in `useEffect` | Prevents hydration error | Double-paint: server renders no splash, client adds it, causing flash | **Never** — initialize to `true`, remove in `useEffect` |
| `loading.tsx` for skeleton screens in static export | Works in `next dev` | Silently ignored in production static export | **Never** — use client-side state-based skeletons |
| OG image without `metadataBase` | No error at build time | Social shares show no image; AI engine extraction has no thumbnail | **Never** — add `metadataBase` before any OG image is referenced |
| Uploading to S3 without CloudFront invalidation | Faster deploy script | Stale HTML serves to users for up to 5 minutes post-deploy | **Never after the first SEO/meta changes** — always invalidate on deploy |
| JSON-LD structured data in `"use client"` component | Easy to co-locate with page content | AI crawlers never see it; zero GEO value | **Never** — JSON-LD must be in Server Components |
| `<Image>` without `width`/`height` using `unoptimized: true` | Less boilerplate | CLS failures on every image load; Core Web Vitals damage | **Never for above-the-fold images** — always provide dimensions |
| `robots.txt` generated by `next-sitemap` but not included in S3 sync | Looks done in CI logs | Crawlers receive 403 and treat site as uncrawlable | **Never** — verify with `curl` post-deploy |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **CloudFront SECURITY_HEADERS** | Using the managed policy with Clerk + Google Fonts | Replace with custom `ResponseHeadersPolicy` that allows Clerk FAPI domain, `challenges.cloudflare.com`, `fonts.googleapis.com`, `fonts.gstatic.com` |
| **Clerk (marketing site)** | Adding Clerk to the marketing site for sign-in link | The marketing site does NOT use Clerk — sign-in links are `<a href="https://cofounder.getinsourced.ai/sign-in">` external links; Clerk is only in the `frontend/` app |
| **next-sitemap** | Running it in `prebuild` instead of `postbuild` | `next-sitemap` must run AFTER `next build` — it reads the `out/` directory; in `prebuild` it reads an empty directory |
| **NProgress / next-nprogress-bar** | Using App Router's built-in router events (`useRouter().events`) | App Router has no `router.events` API; use `next-nprogress-bar` which patches `<Link>` to call `NProgress.start()` manually |
| **Framer Motion in Server Components** | Adding `motion.div` without `"use client"` | Framer Motion requires browser APIs; wrap all animation components in `"use client"` — but keep JSON-LD structured data out of those components |
| **CloudFront invalidation** | Running `aws cloudfront create-invalidation --paths "/*" --paths "/"` (two separate path args) | The `--paths` flag takes a single space-separated list or a JSON `{"Quantity":1,"Items":["/*"]}` — `"/*"` counts as one path, sufficient to invalidate all HTML |
| **Google Fonts in static export** | Using `next/font/google` with `output: "export"` | `next/font/google` works with static export — it downloads and self-hosts fonts at build time. Space Grotesk is already configured correctly in the marketing layout; do NOT switch to a `<link>` tag |
| **S3 sync on deploy** | Using `--exclude "*"` with only specific `--include` patterns | Excludes `robots.txt`, `sitemap.xml`, `favicon.ico`, and other public root files; use `aws s3 sync out/ s3://bucket/ --delete` to sync everything |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **5-minute HTML TTL without forced invalidation on deploy** | Stale marketing pages after every deploy | Add `aws cloudfront create-invalidation` as the final deploy step; or set HTML TTL to 0 | Every deploy that changes HTML, meta tags, or OG data |
| **Framer Motion bundled for the entire marketing site** | Large JS bundle (~90KB gzipped for Framer Motion) loaded on every page even if only the hero uses animation | Code-split Framer Motion with dynamic imports: `const motion = dynamic(() => import('framer-motion').then(m => m.motion), { ssr: false })` | Immediate — visible in Lighthouse bundle analysis |
| **Full-page progress bar for a static site** | Progress bar fires on every link click, even for near-instant navigations between static pages | Add a 100ms delay before showing the progress bar to avoid flicker on fast loads | Any page-to-page navigation on fast connections |
| **`unoptimized: true` + large PNG hero images** | LCP above 2.5s, bandwidth waste for mobile users | Compress images manually to <200KB and use WebP (convert at build time with `next-image-export-optimizer`); CloudFront serves compressed files via Brotli automatically | Immediately visible on Lighthouse — LCP is the primary marketing site metric |
| **JSON-LD as inline string concatenation** | Malformed JSON if page title contains quotes, breaking rich results | Use `JSON.stringify({ ... })` to generate the script content, never string templates | Any page with special characters in title or description |

---

## Security Mistakes

Domain-specific security issues relevant to this milestone.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **Deploying structured data with placeholder content** | AI engines cite incorrect information ("2,000+ founders" claim when number is zero) | Audit all schema.org data for accuracy before deploy; verify `Organization.name`, `sameAs` URLs, and `description` are production-accurate |
| **`robots.txt` that blocks Googlebot on the app domain** | Marketing site robots.txt accidentally has rules that crawlers apply to `cofounder.getinsourced.ai` | `robots.txt` scopes are per-domain — the marketing `robots.txt` at `getinsourced.ai` only applies to `getinsourced.ai`; no cross-domain risk, but verify the domain is correct in sitemap URLs |
| **Wildcard `Allow: /` in robots.txt exposes staging/preview deployments** | If a staging CloudFront distribution shares the same S3 bucket prefix, crawlers index staging content | Use separate S3 buckets for staging and production; staging bucket should have `robots.txt` with `Disallow: /` |
| **OG image fetched from a publicly accessible but unsigned S3 URL** | Exposes bucket name; S3 presigned URLs expire and break caches | Serve OG images through CloudFront (already the case — public S3 URL is not accessible due to OAC BLOCK_ALL policy); verify OG image is in `public/` not referenced as a direct S3 URL |
| **CSP `unsafe-eval` added for debugging** | XSS risk if left in production | Never add `unsafe-eval` to CSP; Framer Motion and all required libraries function without it |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **Splash screen that can't be dismissed or times out too long** | Users on slow connections wait >3s staring at a logo | Cap the splash at 1.5s maximum regardless of asset load state; use a fast CSS opacity transition (300ms) |
| **Skeleton screens with wrong aspect ratios** | When real content loads, it has different dimensions than the skeleton — causes CLS and jarring layout jump | Match skeleton dimensions exactly to real content dimensions; for the chat UI mockup use the same `width`/`height` as the rendered component |
| **Progress bar that shows for <300ms** | Flickering progress bar on fast navigations feels broken | Only show the progress bar after 100ms of navigation pending; use a minimum display duration of 400ms to avoid flicker |
| **Dark-mode-only animations that invert on light system themes** | Non-technical founders using light mode see broken glass effects | The marketing site uses `className="dark"` on `<html>` — this forces dark mode regardless of system preference, which is correct; verify this is preserved after any global CSS changes |
| **Loading skeleton color that clashes with the dark background** | Skeleton is invisible (dark gray on near-black) | Use `bg-white/10 animate-pulse` not `bg-gray-200` (which is invisible on the obsidian background) |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Sitemap:** Generates and appears in `out/sitemap.xml` — verify it was uploaded to S3 with `curl https://getinsourced.ai/sitemap.xml`; verify URLs use the correct domain (`getinsourced.ai`, not `localhost` or a build artifact path)
- [ ] **robots.txt:** Exists at `marketing/public/robots.txt` — verify `curl https://getinsourced.ai/robots.txt` returns 200 with `Sitemap:` line included
- [ ] **OG image:** `<meta property="og:image">` is present in rendered HTML — verify with `curl https://getinsourced.ai/ | grep og:image` returns an absolute URL (`https://getinsourced.ai/og-image.png`), not a relative path
- [ ] **JSON-LD structured data:** Present in static HTML — verify with `curl https://getinsourced.ai/ | grep application/ld+json`; not just visible in DevTools after JS runs
- [ ] **CloudFront invalidation on deploy:** Deploy script ends with an invalidation command — verify by checking CloudFront Invalidations tab in AWS console after each deploy
- [ ] **CSP with Clerk allowlist:** Verify Clerk sign-in page loads correctly after security headers change — test sign-in flow end-to-end in a deployed environment, not just locally
- [ ] **Splash screen server/client parity:** Verify no React hydration error in browser console on the marketing home page — `"use client"` component initializing `showSplash: true`
- [ ] **Skeleton screens in production:** Test skeleton behavior using `next build && npx serve out -p 3001` — not `next dev`; skeletons that only appear in dev mode are a bug
- [ ] **Progress bar timing:** Verify progress bar does not flicker on sub-200ms navigations between static pages — test on localhost with Fast 3G throttling in DevTools
- [ ] **Social preview validation:** Test OG tags with Facebook Sharing Debugger, LinkedIn Post Inspector, and Twitter Card Validator for at least the home page and the `/cofounder` page

---

## Recovery Strategies

When pitfalls occur despite prevention.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **CSP blocks Clerk or analytics post-deploy** | LOW | 1. Update CDK `ResponseHeadersPolicy` with correct `frame-src` / `script-src` 2. `cdk deploy MarketingStack` 3. CloudFront propagates new headers within 5 minutes — no S3 redeploy needed |
| **Hydration mismatch on splash screen** | LOW | 1. Add `suppressHydrationWarning` as a temporary unblock 2. Fix the `useState` initial value pattern 3. Remove `suppressHydrationWarning` after fix is confirmed |
| **Stale HTML after deploy (no invalidation)** | LOW | 1. Run `aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"` manually 2. Verify with private browser window 3. Add invalidation to deploy script permanently |
| **Sitemap shows wrong URLs** | LOW | 1. Fix `next-sitemap.config.js` `siteUrl` value 2. Rebuild 3. Re-sync to S3 4. Invalidate CloudFront 5. Resubmit sitemap in Google Search Console |
| **JSON-LD only in client component** | MEDIUM | 1. Move structured data to the Server Component page or layout 2. Rebuild and deploy 3. Verify with `curl` 4. Request re-crawl in Google Search Console (re-indexing can take days) |
| **OG image not resolving** | LOW | 1. Add `metadataBase` to `layout.tsx` 2. Rebuild 3. Deploy and invalidate 4. Re-scrape with Facebook Debugger (click "Scrape Again") |
| **`loading.tsx` skeletons don't appear in production** | MEDIUM | 1. Convert to client-side `useState`-based skeletons 2. Test with `npx serve out` 3. Redeploy — this requires rewriting skeleton components |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| SECURITY_HEADERS blocks Clerk / third-party scripts | Phase 1 (Security headers audit) | Sign-in flow works end-to-end on deployed site; no CSP errors in browser console |
| Splash screen hydration mismatch | Phase 2 (Loading UX) | No React hydration warning in production; Lighthouse shows 0 hydration errors |
| `loading.tsx` ignored in static export | Phase 2 (Loading UX) | Skeleton screens visible with `npx serve out`; not just in `next dev` |
| Framer Motion large bundle | Phase 3 (Performance) | Lighthouse bundle analysis shows Framer Motion is code-split; main bundle < 150KB |
| Stale HTML after deploy | Phase 3 (Performance / CI) | CloudFront invalidation is the last step in deploy script; verified in AWS console |
| `unoptimized: true` CLS from missing dimensions | Phase 3 (Performance) | Lighthouse CLS < 0.05 on all marketing pages; all `<Image>` components have `width`/`height` |
| Sitemap generation errors | Phase 4 (SEO) | `next-sitemap` runs in `postbuild`; sitemap accessible at `https://getinsourced.ai/sitemap.xml` with correct URLs |
| OG image `metadataBase` missing | Phase 4 (SEO) | `curl https://getinsourced.ai/ | grep og:image` returns absolute URL; Facebook Debugger shows image |
| `robots.txt` missing from S3 | Phase 4 (SEO) | `curl https://getinsourced.ai/robots.txt` returns 200 with correct content |
| JSON-LD in client component only | Phase 5 (GEO) | `curl https://getinsourced.ai/ | grep application/ld+json` returns structured data in static HTML |
| Structured data inaccurate | Phase 5 (GEO) | Google Rich Results Test passes; all schema.org data verified for accuracy against live product state |

---

## Sources

**Next.js Static Export Limitations:**
- [Next.js Static Exports Guide](https://nextjs.org/docs/pages/guides/static-exports) — confirmed `loading.tsx` incompatibility
- [Next.js sitemap.ts with output: export — Bug #59136](https://github.com/vercel/next.js/issues/59136) — confirmed `force-static` requirement
- [trailingSlash + output export bug #68215](https://github.com/vercel/next.js/issues/68215) — confirmed sitemap URL suffix issue

**CloudFront and Security Headers:**
- [AWS CloudFront Managed Response Headers Policies](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-response-headers-policies.html)
- [Clerk CSP Headers Documentation](https://clerk.com/docs/guides/secure/best-practices/csp-headers)
- [COEP and COOP response headers with S3 + CloudFront — AWS re:Post](https://repost.aws/questions/QUVRdl8CFMSF6lDMtj9Lr0gQ/coep-and-coop-response-headers-with-s3-cloudfront)

**CloudFront Caching and Invalidation:**
- [Controlling how long S3 content is cached by CloudFront](https://docs.aws.amazon.com/whitepapers/latest/build-static-websites-aws/controlling-how-long-amazon-s3-content-is-cached-by-amazon-cloudfront.html)
- [CloudFront Invalidation Pricing](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PayingForInvalidation.html)
- [CloudFront continues to serve old content after invalidation — AWS re:Post](https://repost.aws/questions/QUG__vuLtlS-Wf_z2iNxOFtw/cloudfront-continues-to-serve-old-content-after-invalidation-and-s3-update)

**Open Graph and Social Metadata:**
- [Open Graph images not working with Next.js 13 Discussion #50546](https://github.com/vercel/next.js/discussions/50546) — confirmed `metadataBase` requirement
- [Next.js Metadata and OG Images Documentation](https://nextjs.org/docs/app/getting-started/metadata-and-og-images)

**Image Optimization and CLS:**
- [Next.js Image Component Documentation](https://nextjs.org/docs/app/api-reference/components/image)
- [next-image-export-optimizer](https://github.com/Niels-IO/next-image-export-optimizer) — post-build optimization for static exports
- [Fixing CLS issues in Next.js — LogRocket](https://blog.logrocket.com/fix-layout-shifts-improve-seo-next-js/)

**Progress Bar in App Router:**
- [Global progress in Next.js — buildui.com](https://buildui.com/posts/global-progress-in-nextjs)
- [next-nprogress-bar on npm](https://www.npmjs.com/package/next-nprogress-bar)
- [App Router router events missing — Discussion #41934](https://github.com/vercel/next.js/discussions/41934)

**GEO and Structured Data:**
- [Schema for SaaS companies — SALT Agency](https://salt.agency/blog/schema-for-saas-companies-salt-agency/)
- [Schema & Structured Data for LLM Visibility — Quoleady](https://www.quoleady.com/schema-structured-data-for-llm-visibility/)
- [Next.js JSON-LD Guide](https://nextjs.org/docs/app/guides/json-ld)
- [Structured data: SEO and GEO optimization for AI — Digidop](https://www.digidop.com/blog/structured-data-secret-weapon-seo)

**Font Optimization:**
- [Next.js Font Optimization Documentation](https://nextjs.org/docs/app/getting-started/fonts)
- [Custom fonts without compromise using next/font — Vercel](https://vercel.com/blog/nextjs-next-font)

---

*Pitfalls research for: Premium loading UX, performance optimization, SEO, and GEO — Next.js static export on CloudFront + S3*
*Researched: 2026-02-20*
