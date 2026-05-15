import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Restaurer une photo — Flashback Restore',
  description: "Restaurez vos photos anciennes avec l'IA. Réparation automatique des défauts, rayures et taches.",
  openGraph: { images: ['/og-default.jpg'] },
};

export default function RestoreLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
