import type { Metadata } from "next";
import { Suspense } from "react";
import RestoreClient from "./RestoreClient";

export const metadata: Metadata = {
  title: "Restaurer vos photos — Flashback Restore",
  description: "Réparez automatiquement les défauts, rayures et taches de vos photos anciennes grâce à l'IA.",
};

export default function Page() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="animate-pulse text-muted">Chargement...</div></div>}>
      <RestoreClient />
    </Suspense>
  );
}
