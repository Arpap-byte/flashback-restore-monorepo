import type { Metadata } from "next";
import RestoreClient from "./RestoreClient";

export const metadata: Metadata = {
  title: "Restaurer vos photos — Flashback Restore",
  description: "Réparez automatiquement les défauts, rayures et taches de vos photos anciennes grâce à l'IA.",
};

export default function Page() {
  return <RestoreClient />;
}
