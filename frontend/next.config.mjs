// The browser always calls this app's own /api, and Next.js forwards it to the
// gateway. Only port 3000 then has to be reachable from other laptops, and no
// gateway address is baked into the client bundle. Read at build time.
const apiProxyTarget = (process.env.API_PROXY_TARGET || 'http://localhost:8000').replace(/\/$/, '');

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${apiProxyTarget}/api/:path*` }];
  },
};

export default nextConfig;
