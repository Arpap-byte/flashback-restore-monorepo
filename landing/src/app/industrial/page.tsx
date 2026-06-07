import type { Metadata } from "next";
import IndustrialContent from "./IndustrialContent";

export const metadata: Metadata = {
  title: "Solutions par industrie — Flashback Restore",
  description:
    "Découvrez comment Flashback Restore s'adapte à votre secteur : photographie, musées, généalogie, presse, mode, enseignement et bien plus. Restauration et animation de photos par IA.",
  openGraph: {
    title: "Solutions par industrie — Flashback Restore",
    description:
      "Découvrez comment Flashback Restore s'adapte à votre secteur : photographie, musées, généalogie, presse, mode, enseignement et bien plus.",
    url: "https://flashback-restore.com/industrial",
    type: "website",
    locale: "fr_FR",
    siteName: "Flashback Restore",
  },
  robots: "index, follow",
};

export default function IndustrialPage() {
  return <IndustrialContent />;
}
