import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Animer une photo — Flashback Restore',
  description: "Donnez vie à vos photos avec l'animation IA. Transformez un portrait en vidéo réaliste.",
  openGraph: { images: ['/og-default.jpg'] },
};

export default function AnimateLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
