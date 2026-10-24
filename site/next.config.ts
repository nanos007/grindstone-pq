import type { NextConfig } from "next";

// Static export: `npm run build` writes a self-contained site to out/ (GitHub Pages, any static host).
// GitHub Pages serves the project at nanos007.github.io/grindstone-pq: build with NEXT_PUBLIC_BASE_PATH=/grindstone-pq.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  basePath,
};

export default nextConfig;
