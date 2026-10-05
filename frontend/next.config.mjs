/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const dest = process.env.INTERNAL_API_URL || "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${dest}/api/:path*` },
      { source: "/health", destination: `${dest}/health` },
    ];
  },

};

export default nextConfig;
