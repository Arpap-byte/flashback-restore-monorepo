import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Historique — Flashback Restore',
  description: 'Retrouvez toutes vos photos restaurées et animées. Gérez votre historique de travaux.',
  openGraph: { images: ['/og-default.jpg'] },
};

export default function HistoriqueLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
