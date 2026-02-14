import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable React strict mode
  reactStrictMode: true,
  // Enable standalone output for Docker
  output: "standalone",
};

export default nextConfig;
