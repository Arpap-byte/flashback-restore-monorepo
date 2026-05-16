import { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = "https://flashback-restore.com";

  const routes = [
    "",
    "/restore",
    "/animate",
    "/dashboard",
    "/historique",
    "/abonnement/succes",
    "/about",
    "/privacy",
    "/terms",
    "/cookies",
    "/business",
  ].map((route) => ({
    url: `${baseUrl}${route}`,
    lastModified: new Date(),
    changeFrequency: route === "" ? ("weekly" as const) : ("monthly" as const),
    priority: route === "" ? 1 : 0.8,
  }));

  return routes;
}
