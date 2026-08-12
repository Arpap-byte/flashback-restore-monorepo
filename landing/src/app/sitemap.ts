import { MetadataRoute } from "next";
import { getAllSlugs } from "@/lib/blog-posts";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = "https://flashback-restore.com";

  const staticRoutes = [
    { route: "", changeFrequency: "weekly" as const, priority: 1 },
    { route: "/about", changeFrequency: "monthly" as const, priority: 0.7 },
    { route: "/credits", changeFrequency: "monthly" as const, priority: 0.7 },
    { route: "/business", changeFrequency: "monthly" as const, priority: 0.6 },
    { route: "/industrial", changeFrequency: "monthly" as const, priority: 0.6 },
    { route: "/blog", changeFrequency: "weekly" as const, priority: 0.8 },
    { route: "/privacy", changeFrequency: "yearly" as const, priority: 0.3 },
    { route: "/terms", changeFrequency: "yearly" as const, priority: 0.3 },
    { route: "/cookies", changeFrequency: "yearly" as const, priority: 0.3 },
  ];

  const blogRoutes = getAllSlugs().map((slug) => ({
    route: `/blog/${slug}`,
    changeFrequency: "monthly" as const,
    priority: 0.7,
  }));

  const allRoutes = [...staticRoutes, ...blogRoutes];

  return allRoutes.map(({ route, changeFrequency, priority }) => ({
    url: `${baseUrl}${route}`,
    lastModified: new Date(),
    changeFrequency,
    priority,
  }));
}
