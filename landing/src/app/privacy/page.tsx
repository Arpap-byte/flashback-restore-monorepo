"use client";

import { motion } from "framer-motion";
import { Shield, Lock, Eye, Trash2, Mail, ChevronRight } from "lucide-react";
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
    icon: Shield,
    title: "1. Introduction",
    content:
      "Flashback Restore (\"nous\", \"notre\", \"nos\") s'engage à protéger votre vie privée. Cette Politique de Confidentialité explique comment nous collectons, utilisons, divulguons et protégeons vos informations personnelles lorsque vous utilisez notre service de restauration et d'animation de photos par intelligence artificielle, accessible sur flashback-restore.com (le \"Service\").",
  },
  {
    icon: Eye,
    title: "2. Données que nous collectons",
    content: "",
    bullets: [
      "Informations de compte : adresse e-mail lorsque vous vous connectez via authentification (Google, email).",
      "Données d'utilisation : statistiques d'utilisation de l'application, pages visitées, fonctionnalités utilisées, durée des sessions. Ces données sont collectées via des outils d'analyse anonymisés.",
      "Images téléchargées : les photos que vous importez pour restauration ou animation. Ces images sont traitées temporairement sur nos serveurs sécurisés. Nous ne conservons pas vos images après le traitement, sauf si vous donnez votre consentement explicite pour les stocker (par exemple, pour conserver un historique de vos restaurations).",
      "Données de paiement : les informations de transaction sont traitées exclusivement par notre partenaire de paiement Stripe. Nous ne stockons jamais vos données bancaires complètes.",
      "Cookies et technologies similaires : voir notre Politique de Cookies pour plus de détails.",
    ],
  },
  {
    icon: Lock,
    title: "3. Comment nous utilisons vos données",
    content: "",
    bullets: [
      "Fournir, maintenir et améliorer notre Service de restauration photo IA.",
      "Vous authentifier et sécuriser votre compte.",
      "Traiter vos images pour la restauration et l'animation (traitement temporaire).",
      "Communiquer avec vous : notifications de service, assistance client, mises à jour produit (avec votre consentement).",
      "Analyser l'utilisation du Service pour améliorer nos algorithmes et l'expérience utilisateur.",
      "Prévenir la fraude et garantir la sécurité de notre plateforme.",
    ],
  },
  {
    icon: Trash2,
    title: "4. Conservation des données",
    content:
      "Nous conservons vos données personnelles uniquement pendant la durée nécessaire aux finalités décrites ci-dessus. Les images téléchargées sont supprimées de nos serveurs immédiatement après le traitement, sauf si vous avez donné votre consentement explicite pour leur conservation. Les données de compte sont conservées tant que votre compte est actif. Vous pouvez demander la suppression de vos données à tout moment.",
  },
  {
    icon: Shield,
    title: "5. Partage et divulgation",
    content: "",
    bullets: [
      "Nous ne vendons jamais vos données personnelles à des tiers.",
      "Nous pouvons partager des données avec des sous-traitants de confiance (hébergement cloud, IA, analyse) qui nous aident à fournir le Service. Ces partenaires sont liés par des clauses de confidentialité strictes.",
      "Nous pouvons divulguer des informations si la loi l'exige ou pour protéger nos droits légaux.",
      "Les images sont traitées via des services tiers d'IA uniquement aux fins de restauration et d'animation, sans conservation par ces tiers au-delà du traitement.",
    ],
  },
  {
    icon: Lock,
    title: "6. Sécurité",
    content:
      "Nous mettons en œuvre des mesures de sécurité techniques et organisationnelles appropriées pour protéger vos données : chiffrement en transit (TLS 1.3) et au repos (AES-256), serveurs sécurisés situés dans l'Union Européenne, accès restreint aux données aux seuls employés autorisés, audits de sécurité réguliers, authentification forte et surveillance continue des systèmes.",
  },
  {
    icon: Shield,
    title: "7. Protection des mineurs",
    content:
      "Notre Service n'est pas destiné aux personnes de moins de 13 ans. Nous ne collectons pas sciemment de données personnelles auprès d'enfants de moins de 13 ans. Si vous êtes un parent ou tuteur et pensez que votre enfant nous a fourni des informations personnelles, veuillez nous contacter immédiatement.",
  },
  {
    icon: Eye,
    title: "8. Vos droits",
    content: "",
    bullets: [
      "Droit d'accès : vous pouvez demander une copie des données personnelles que nous détenons à votre sujet.",
      "Droit de rectification : vous pouvez corriger toute information inexacte ou incomplète.",
      "Droit à l'effacement : vous pouvez demander la suppression de vos données personnelles (\"droit à l'oubli\").",
      "Droit à la portabilité : vous pouvez recevoir vos données dans un format structuré et lisible.",
      "Droit d'opposition : vous pouvez vous opposer au traitement de vos données pour des motifs légitimes.",
      "Droit de retirer votre consentement à tout moment, sans affecter la licéité du traitement antérieur.",
    ],
    extra:
      "Pour exercer ces droits, contactez-nous à apexcyber.eu@gmail.com. Nous répondrons dans un délai de 30 jours conformément au RGPD.",
  },
  {
    icon: Mail,
    title: "9. Contact",
    content:
      "Pour toute question concernant cette Politique de Confidentialité ou pour exercer vos droits, contactez-nous à :",
    contact: {
      email: "apexcyber.eu@gmail.com",
      label: "Nous contacter par email",
    },
  },
  {
    icon: Shield,
    title: "10. Modifications",
    content:
      "Nous pouvons mettre à jour cette Politique de Confidentialité périodiquement. Nous vous informerons de tout changement significatif par email ou via une notification sur notre Service. La date de dernière mise à jour est indiquée ci-dessous.",
  },
];

export default function PrivacyPage() {
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
              <Shield className="w-4 h-4" />
              Protection des données
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              Politique de{" "}
              <span className="text-gradient">Confidentialité</span>
            </h1>
            <p className="text-muted text-lg max-w-xl mx-auto">
              Nous prenons votre vie privée au sérieux. Découvrez comment nous
              protégeons vos données et vos souvenirs.
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
              <span className="text-foreground">Politique de Confidentialité</span>
            </div>
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
                          <Mail className="w-4 h-4" />
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
              Des questions sur vos données ?
            </h3>
            <p className="text-muted mb-4">
              Notre équipe est là pour vous répondre.
            </p>
            <a
              href="mailto:apexcyber.eu@gmail.com"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold hover:brightness-110 transition-all hover:shadow-lg hover:shadow-accent/25"
            >
              <Mail className="w-4 h-4" />
              apexcyber.eu@gmail.com
            </a>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
