import type { Metadata } from "next";
import HistoriqueClient from "./HistoriqueClient";

export const metadata: Metadata = {
  title: "Historique — Flashback Restore",
  description: "Retrouvez toutes vos photos restaurées et animées.",
};

export default function Page() {
  return <HistoriqueClient />;
}
