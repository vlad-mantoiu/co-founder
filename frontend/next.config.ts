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
};

export default nextConfig;
