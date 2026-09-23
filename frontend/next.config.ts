import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const mocking = process.env.NEXT_PUBLIC_API_MOCKING === "1";

const nextConfig: NextConfig = {
  output: "standalone",
  // Same-origin proxy so the backend's httpOnly cookie is first-party.
  // Disabled in mock mode: MSW answers in the browser.
  async rewrites() {
    return mocking ? [] : [{ source: "/api/v1/:path*", destination: `${BACKEND_URL}/api/v1/:path*` }];
  },
};

export default withNextIntl(nextConfig);
