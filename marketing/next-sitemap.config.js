/** @type {import('next-sitemap').IConfig} */
module.exports = {
  siteUrl: 'https://getinsourced.ai',
  output: 'export',
  outDir: 'out',
  generateRobotsTxt: true,
  generateIndexSitemap: false,
  autoLastmod: true,
  changefreq: 'weekly',
  priority: 0.7,
  trailingSlash: true,
  exclude: ['/404', '/404/'],
  robotsTxtOptions: {
    policies: [
      { userAgent: '*', allow: '/' },
    ],
  },
}
