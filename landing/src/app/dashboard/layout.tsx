import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Tableau de bord — Flashback Restore',
  description: 'Gérez votre compte, vos crédits et suivez vos restaurations de photos.',
  openGraph: { images: ['/og-default.jpg'] },
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
