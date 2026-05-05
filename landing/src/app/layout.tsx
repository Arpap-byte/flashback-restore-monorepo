import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import { ThemeProvider } from "@/components/ThemeProvider";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const playfair = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "Flashback Restore — Redonnez vie à vos souvenirs avec l'IA",
  description:
    "Restaurez et animez vos photos anciennes grâce à l'intelligence artificielle. Donnez une seconde vie à vos souvenirs de famille en quelques secondes.",
  keywords: [
    "restauration photo",
    "animation photo",
    "intelligence artificielle",
    "photos anciennes",
    "souvenirs de famille",
    "Flashback Restore",
    "Gemini AI",
    "D-ID",
  ],
  openGraph: {
    title: "Flashback Restore — Redonnez vie à vos souvenirs",
    description:
      "Restaurez et animez vos photos anciennes grâce à l'intelligence artificielle.",
    type: "website",
    locale: "fr_FR",
    siteName: "Flashback Restore",
  },
  twitter: {
    card: "summary_large_image",
    title: "Flashback Restore — Redonnez vie à vos souvenirs",
    description:
      "Restaurez et animez vos photos anciennes grâce à l'intelligence artificielle.",
  },
  robots: "index, follow",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="fr"
      className={`${inter.variable} ${playfair.variable} h-full antialiased dark`}
      suppressHydrationWarning
    >
      <body className="min-h-full bg-background text-foreground font-sans transition-colors">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
