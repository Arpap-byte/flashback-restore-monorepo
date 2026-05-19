import type { NextConfig } from "next";
import withSerwistInit from "@serwist/next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: '/upload',
        destination: '/restore',
        permanent: true,
      },
      // Redirections canoniques françaises (Bug #5)
      {
        source: '/cgu',
        destination: '/conditions-utilisation',
        permanent: true,
      },
      {
        source: '/confidentialite',
        destination: '/privacy',
        permanent: true,
      },
      {
        source: '/tarifs',
        destination: '/#pricing',
        permanent: true,
      },
      {
        source: '/pricing',
        destination: '/#pricing',
        permanent: true,
      },
      {
        source: '/legal',
        destination: '/mentions-legales',
        permanent: true,
      },
      {
        source: '/contact',
        destination: '/#footer',
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
          { key: 'Content-Security-Policy', value: "default-src 'self'; script-src 'self' 'unsafe-inline' https://js.stripe.com https://*.clerk.accounts.dev https://challenges.cloudflare.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; frame-src https://js.stripe.com https://*.clerk.accounts.dev https://challenges.cloudflare.com; connect-src 'self' https://api.stripe.com https://*.clerk.accounts.dev https://challenges.cloudflare.com" },
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

const withSerwist = withSerwistInit({
  swSrc: "src/app/sw.ts",
  swDest: "public/sw.js",
});

export default withSerwist(nextConfig);
