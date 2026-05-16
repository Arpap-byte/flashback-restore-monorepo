import type { Metadata } from "next";
import DashboardClient from "./DashboardClient";

export const metadata: Metadata = {
  title: "Tableau de bord — Flashback Restore",
  description: "Gérez vos crédits, vos restaurations et votre abonnement.",
};

export default function Page() {
  return <DashboardClient />;
}
