import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: '/upload',
        destination: '/restore',
        permanent: true,
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
          { key: 'Content-Security-Policy', value: "default-src 'self'; script-src 'self' 'unsafe-inline' https://js.stripe.com https://*.clerk.accounts.dev; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; frame-src https://js.stripe.com https://*.clerk.accounts.dev; connect-src 'self' https://api.stripe.com https://*.clerk.accounts.dev" },
        ],
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "flashback-restore.com",
      },
      {
        protocol: "http",
        hostname: "148.230.116.52",
        port: "8000",
        pathname: "/uploads/**",
      },
    ],
  },
};

export default nextConfig;
