// CloudFront Function for marketing site (JS 2.0 runtime, viewer request)
// Handles: www-to-apex 301 redirect + clean URL rewriting for Next.js static export
async function handler(event) {
  var request = event.request;
  var host = request.headers.host.value;
  var uri = request.uri;

  // 1. www -> apex 301 redirect (SEO best practice)
  if (host.startsWith('www.')) {
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: {
        'location': { value: 'https://getinsourced.ai' + uri }
      }
    };
  }

  // 2. Clean URL rewriting: /about -> /about/index.html
  // Next.js static export generates directory-style output (about/index.html, not about.html)
  // Skip root "/" (handled by defaultRootObject: 'index.html')
  // Skip paths with file extensions (e.g. /_next/static/..., /favicon.ico)
  // Skip paths ending with "/"
  if (uri !== '/' && !uri.includes('.') && !uri.endsWith('/')) {
    request.uri = uri + '/index.html';
    return request;
  }

  // 3. Trailing slash: /about/ -> /about/index.html
  // Skip root "/" which is handled by defaultRootObject
  if (uri.endsWith('/') && uri !== '/') {
    request.uri = uri + 'index.html';
  }

  return request;
}
