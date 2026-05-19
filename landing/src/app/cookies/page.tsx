"use client";

import { motion } from "framer-motion";
import { Cookie, Shield, Settings, Info, ChevronRight } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import Link from "next/link";

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5 },
};

const stagger = {
  animate: {
    transition: { staggerChildren: 0.1 },
  },
};

const sections = [
  {
    icon: Info,
    title: "1. Qu'est-ce qu'un cookie ?",
    content:
      "Un cookie est un petit fichier texte déposé sur votre appareil (ordinateur, tablette, smartphone) lors de la consultation d'un site web. Les cookies permettent au site de reconnaître votre navigateur et de mémoriser certaines informations pendant une durée déterminée, comme vos préférences de langue ou de thème. Ils ne contiennent pas de virus et ne peuvent pas accéder à d'autres données de votre appareil.",
  },
  {
    icon: Cookie,
    title: "2. Cookies que nous utilisons",
    content:
      "Flashback Restore utilise uniquement des cookies strictement nécessaires au fonctionnement du Service. Nous ne déposons pas de cookies publicitaires ou de tracking tiers.",
  },
  {
    icon: Settings,
    title: "3. Détail des cookies",
    content: "",
    table: [
      {
        name: "theme",
        domain: "flashback-restore.com",
        purpose: "Stocke votre préférence de thème (clair ou sombre) pour une expérience visuelle cohérente.",
        duration: "1 an",
        category: "Préférence (strictement nécessaire)",
      },
      {
        name: "auth_session",
        domain: "flashback-restore.com",
        purpose: "Maintient votre session d'authentification pour éviter de devoir vous reconnecter à chaque page.",
        duration: "Session (supprimé à la fermeture du navigateur)",
        category: "Authentification (strictement nécessaire)",
      },
      {
        name: "stripe_session",
        domain: "stripe.com",
        purpose: "Cookie déposé par Stripe, notre prestataire de paiement, pour sécuriser les transactions.",
        duration: "Session",
        category: "Paiement (strictement nécessaire)",
      },
      {
        name: "cf_clearance",
        domain: "flashback-restore.com",
        purpose: "Cookie de sécurité Cloudflare pour protéger le site contre les attaques et les bots malveillants.",
        duration: "30 minutes",
        category: "Sécurité (strictement nécessaire)",
      },
    ],
  },
  {
    icon: Shield,
    title: "4. Base légale",
    content:
      "Conformément au Règlement Général sur la Protection des Données (RGPD) et à la directive ePrivacy, les cookies strictement nécessaires au fonctionnement du Service sont exemptés de l'obligation de recueil du consentement (Article 82 de la loi Informatique et Libertés). Ces cookies ne collectent pas de données personnelles à des fins publicitaires et ne permettent pas de suivre votre navigation sur d'autres sites.",
  },
  {
    icon: Settings,
    title: "5. Comment gérer les cookies",
    content:
      "Vous pouvez à tout moment configurer votre navigateur pour bloquer, supprimer ou être alerté de l'utilisation des cookies :",
    bullets: [
      "Google Chrome : Paramètres → Confidentialité et sécurité → Cookies et autres données de site.",
      "Mozilla Firefox : Options → Vie privée et sécurité → Cookies et données de site.",
      "Safari : Préférences → Confidentialité → Cookies et données de site web.",
      "Microsoft Edge : Paramètres → Cookies et autorisations de site → Cookies et données stockées.",
    ],
    extra:
      "Important : le blocage des cookies strictement nécessaires peut empêcher le bon fonctionnement du Service (authentification, préférences d'affichage, paiement sécurisé).",
  },
  {
    icon: Info,
    title: "6. Modifications de cette politique",
    content:
      "Nous pouvons mettre à jour cette Politique de Cookies pour refléter des changements dans nos pratiques ou pour des raisons légales. Toute modification sera publiée sur cette page avec une date de mise à jour révisée.",
  },
  {
    icon: Shield,
    title: "7. Contact",
    content:
      "Pour toute question concernant notre utilisation des cookies, vous pouvez nous contacter à :",
    contact: {
      email: "apexcyber.eu@gmail.com",
      label: "Nous contacter",
    },
  },
];

export default function CookiesPage() {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 pt-28 pb-16">
        {/* Background glows */}
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/4 w-[700px] h-[700px] bg-violet-600/5 rounded-full blur-[130px]" />
          <div className="absolute bottom-1/3 right-1/4 w-[600px] h-[600px] bg-accent/4 rounded-full blur-[110px]" />
        </div>

        <div className="relative z-10 max-w-3xl mx-auto px-4 sm:px-6">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 border border-accent/20 text-accent text-sm font-medium mb-6">
              <Cookie className="w-4 h-4" />
              Transparence
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              Politique de{" "}
              <span className="text-gradient">Cookies</span>
            </h1>
            <p className="text-muted text-lg max-w-xl mx-auto">
              Nous utilisons uniquement les cookies strictement nécessaires au
              bon fonctionnement du Service. Aucun tracking publicitaire.
            </p>
            <p className="text-muted/60 text-sm mt-4">
              Dernière mise à jour : 1er mai 2026
            </p>
          </motion.div>

          {/* Breadcrumb */}
          <motion.div {...fadeUp} className="mb-12">
            <div className="flex items-center gap-2 text-sm text-muted">
              <Link href="/" className="hover:text-accent transition-colors">
                Accueil
              </Link>
              <ChevronRight className="w-4 h-4" />
              <span className="text-foreground">Politique de Cookies</span>
            </div>
          </motion.div>

          {/* No tracking highlight */}
          <motion.div
            {...fadeUp}
            className="mb-10 p-5 rounded-2xl bg-emerald-500/5 border border-emerald-500/20 flex items-start gap-3"
          >
            <Shield className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            <p className="text-muted text-sm leading-relaxed">
              <strong className="text-foreground">Respect de votre vie privée :</strong>{" "}
              Flashback Restore n&apos;utilise aucun cookie publicitaire, aucun
              mouchard de tracking tiers, et ne revend aucune donnée. Nous
              utilisons exclusivement des cookies techniques indispensables au
              fonctionnement du Service.
            </p>
          </motion.div>

          {/* Content sections */}
          <motion.div
            variants={stagger}
            initial="initial"
            animate="animate"
            className="space-y-8"
          >
            {sections.map((section, i) => (
              <motion.div
                key={i}
                variants={fadeUp}
                className="bg-card border border-card-border rounded-2xl p-6 sm:p-8 hover:border-muted/50 transition-colors"
              >
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <section.icon className="w-5 h-5 text-accent" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-foreground mb-3 font-[family-name:var(--font-playfair)]">
                      {section.title}
                    </h3>
                    {section.content && (
                      <p className="text-muted leading-relaxed text-sm sm:text-base">
                        {section.content}
                      </p>
                    )}
                    {section.bullets && (
                      <ul className="space-y-2 mt-2">
                        {section.bullets.map((bullet, j) => (
                          <li
                            key={j}
                            className="flex items-start gap-2 text-muted leading-relaxed text-sm sm:text-base"
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-accent/60 flex-shrink-0 mt-2" />
                            {bullet}
                          </li>
                        ))}
                      </ul>
                    )}
                    {section.table && (
                      <div className="mt-3 overflow-x-auto -mx-2 px-2">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-card-border">
                              <th className="text-left py-3 pr-4 text-foreground font-semibold">
                                Cookie
                              </th>
                              <th className="text-left py-3 pr-4 text-foreground font-semibold">
                                Domaine
                              </th>
                              <th className="text-left py-3 pr-4 text-foreground font-semibold">
                                Finalité
                              </th>
                              <th className="text-left py-3 pr-4 text-foreground font-semibold">
                                Durée
                              </th>
                              <th className="text-left py-3 text-foreground font-semibold">
                                Catégorie
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {section.table.map((row, j) => (
                              <tr
                                key={j}
                                className="border-b border-card-border/50 last:border-b-0"
                              >
                                <td className="py-3 pr-4 text-muted font-mono text-xs">
                                  {row.name}
                                </td>
                                <td className="py-3 pr-4 text-muted text-xs">
                                  {row.domain}
                                </td>
                                <td className="py-3 pr-4 text-muted">
                                  {row.purpose}
                                </td>
                                <td className="py-3 pr-4 text-muted whitespace-nowrap">
                                  {row.duration}
                                </td>
                                <td className="py-3 text-muted">
                                  <span className="inline-flex px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs">
                                    {row.category}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                    {section.extra && (
                      <p className="text-muted leading-relaxed text-sm sm:text-base mt-3">
                        {section.extra}
                      </p>
                    )}
                    {section.contact && (
                      <div className="mt-3">
                        <a
                          href={`mailto:${section.contact.email}`}
                          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-accent/10 border border-accent/20 text-accent hover:bg-accent/20 transition-all text-sm font-medium"
                        >
                          <Cookie className="w-4 h-4" />
                          {section.contact.label}
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>

          {/* CTA */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="mt-12 text-center p-8 rounded-2xl bg-gradient-to-br from-accent/5 via-violet-500/5 to-transparent border border-card-border"
          >
            <Shield className="w-8 h-8 text-accent mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-foreground mb-2 font-[family-name:var(--font-playfair)]">
              Des questions sur les cookies ?
            </h3>
            <p className="text-muted mb-4">
              Nous sommes transparents sur notre utilisation des données.
            </p>
            <a
              href="mailto:apexcyber.eu@gmail.com"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold hover:brightness-110 transition-all hover:shadow-lg hover:shadow-accent/25"
            >
              <Cookie className="w-4 h-4" />
              apexcyber.eu@gmail.com
            </a>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
