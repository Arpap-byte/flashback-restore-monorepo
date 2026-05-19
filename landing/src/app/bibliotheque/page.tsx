import type { Metadata } from "next";
import BibliothequeClient from "./BibliothequeClient";

export const metadata: Metadata = {
  title: "Ma bibliothèque — Flashback Restore",
  description: "Gérez vos images importées pour la restauration et l'animation.",
  robots: "noindex, nofollow",
};

export default function Page() {
  return <BibliothequeClient />;
}
