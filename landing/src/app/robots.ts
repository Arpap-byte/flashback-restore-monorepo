import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/admin/", "/api/", "/sign-in/", "/sign-up/", "/auth/"],
    },
    sitemap: "https://flashback-restore.com/sitemap.xml",
  };
}
