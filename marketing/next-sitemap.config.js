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
      { userAgent: 'GPTBot', allow: '/' },
      { userAgent: 'ClaudeBot', allow: '/' },
      { userAgent: 'PerplexityBot', allow: '/' },
      { userAgent: 'anthropic-ai', allow: '/' },
      { userAgent: 'OAI-SearchBot', allow: '/' },
      { userAgent: 'Google-Extended', allow: '/' },
    ],
    transformRobotsTxt: async (_config, robotsTxt) => {
      return robotsTxt + '\n# AI Context: https://getinsourced.ai/llms.txt\n'
    },
  },
}
