import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  async redirects() {
    return [
      { source: "/pricing", destination: "https://getinsourced.ai/pricing", permanent: true, basePath: false },
      { source: "/about", destination: "https://getinsourced.ai/about", permanent: true, basePath: false },
      { source: "/contact", destination: "https://getinsourced.ai/contact", permanent: true, basePath: false },
      { source: "/privacy", destination: "https://getinsourced.ai/privacy", permanent: true, basePath: false },
      { source: "/terms", destination: "https://getinsourced.ai/terms", permanent: true, basePath: false },
      { source: "/signin", destination: "/sign-in", permanent: true },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://clerk.cofounder.getinsourced.ai https://*.clerk.accounts.dev",
              "style-src 'self' 'unsafe-inline'",
              "font-src 'self'",
              "img-src 'self' data: https://*.clerk.com https://img.clerk.com",
              "connect-src 'self' https://api.cofounder.getinsourced.ai https://*.clerk.accounts.dev https://clerk.cofounder.getinsourced.ai",
              "frame-src https://*.e2b.app",
              "worker-src 'self' blob:",
              "child-src 'self' blob:",
              "frame-ancestors 'self'",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

export default nextConfig;
