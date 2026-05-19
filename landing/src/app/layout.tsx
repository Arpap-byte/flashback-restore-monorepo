import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import { ThemeProvider } from "@/components/ThemeProvider";
import { AuthProvider } from "@/context/AuthContext";
import { ClerkProvider } from "@clerk/nextjs";
import { frFR } from "@clerk/localizations";
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
  metadataBase: new URL("https://flashback-restore.com"),
  title: "Flashback Restore — Restauration et colorisation de photos par IA",
  description:
    "Restaurez, colorisez et retouchez vos photos anciennes grâce à l'intelligence artificielle. Redonnez vie à vos souvenirs de famille en quelques secondes.",
  keywords: [
    "restauration photo",
    "colorisation photo",
    "retouche photo",
    "restauration image",
    "photo ancienne",
    "intelligence artificielle",
    "animation photo",
    "souvenirs de famille",
    "Flashback Restore",
  ],
  openGraph: {
    title: "Flashback Restore — Restauration et colorisation de photos par IA",
    description:
      "Restaurez, colorisez et retouchez vos photos anciennes grâce à l'intelligence artificielle. Essayez gratuitement.",
    url: "https://flashback-restore.com",
    type: "website",
    locale: "fr_FR",
    siteName: "Flashback Restore",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Flashback Restore — Restauration et colorisation de photos par IA",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Flashback Restore — Restauration et colorisation de photos",
    description:
      "Restaurez, colorisez et retouchez vos photos anciennes grâce à l'intelligence artificielle.",
    images: ["/og-image.png"],
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
      className={`${inter.variable} ${playfair.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#0a0a0a" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="Flashback" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
        <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
      </head>
      <body className="min-h-full bg-background text-foreground font-sans transition-colors">
        <ClerkProvider localization={frFR}>
          <ThemeProvider>
            <AuthProvider>{children}</AuthProvider>
          </ThemeProvider>
        </ClerkProvider>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "Organization",
              "name": "Flashback Restore",
              "url": "https://flashback-restore.com",
              "description":
                "Restaurez et animez vos photos anciennes grâce à l'intelligence artificielle",
              "sameAs": [],
            }),
          }}
        />
      </body>
    </html>
  );
}
