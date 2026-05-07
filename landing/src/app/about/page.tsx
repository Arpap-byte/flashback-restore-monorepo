"use client";

import { motion } from "framer-motion";
import {
  Sparkles,
  Heart,
  Globe,
  Camera,
  Wand2,
  Shield,
  ChevronRight,
  Check,
} from "lucide-react";
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

const values = [
  {
    icon: Heart,
    title: "Préserver les souvenirs",
    description:
      "Chaque photo ancienne raconte une histoire. Notre mission est de redonner vie à ces moments précieux pour les transmettre aux générations futures.",
  },
  {
    icon: Wand2,
    title: "IA au service de l'humain",
    description:
      "Nous utilisons les technologies d'intelligence artificielle les plus avancées pour restaurer et animer vos photos avec un réalisme impressionnant.",
  },
  {
    icon: Shield,
    title: "Respect de votre vie privée",
    description:
      "Vos souvenirs vous appartiennent. Nous ne conservons jamais vos photos sans votre consentement explicite et ne revendons aucune donnée.",
  },
  {
    icon: Globe,
    title: "Accessible à tous",
    description:
      "Pas besoin d'être un expert. Notre interface simple et intuitive permet à chacun de restaurer ses photos en quelques clics, sans compétence technique.",
  },
];

const stats = [
  { value: "100 000+", label: "Photos restaurées" },
  { value: "50+", label: "Pays" },
  { value: "4.9/5", label: "Satisfaction client" },
  { value: "24/7", label: "Support" },
];

export default function AboutPage() {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 pt-28 pb-16">
        {/* Background glows */}
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/4 w-[700px] h-[700px] bg-violet-600/5 rounded-full blur-[130px]" />
          <div className="absolute bottom-1/3 right-1/4 w-[600px] h-[600px] bg-accent/4 rounded-full blur-[110px]" />
        </div>

        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 border border-accent/20 text-accent text-sm font-medium mb-6">
              <Sparkles className="w-4 h-4" />
              Notre Histoire
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              À propos de{" "}
              <span className="text-gradient">Flashback Restore</span>
            </h1>
            <p className="text-muted text-lg max-w-2xl mx-auto">
              Nous redonnons vie aux souvenirs grâce à l&apos;intelligence
              artificielle. Chaque photo restaurée est une histoire qui continue.
            </p>
          </motion.div>

          {/* Breadcrumb */}
          <motion.div {...fadeUp} className="mb-12">
            <div className="flex items-center gap-2 text-sm text-muted">
              <Link href="/" className="hover:text-accent transition-colors">
                Accueil
              </Link>
              <ChevronRight className="w-4 h-4" />
              <span className="text-foreground">À propos</span>
            </div>
          </motion.div>

          {/* Mission statement */}
          <motion.div
            {...fadeUp}
            className="mb-16"
          >
            <div className="relative rounded-3xl overflow-hidden bg-gradient-to-br from-accent/10 via-card to-violet-500/5 border border-card-border p-8 sm:p-12">
              {/* Decorative blobs */}
              <div className="absolute top-0 right-0 w-64 h-64 bg-accent/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2" />
              <div className="absolute bottom-0 left-0 w-48 h-48 bg-violet-500/10 rounded-full blur-[60px] translate-y-1/2 -translate-x-1/2" />

              <div className="relative">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-500 to-violet-600 flex items-center justify-center shadow-lg shadow-accent/25">
                    <Camera className="w-7 h-7 text-white" />
                  </div>
                  <div>
                    <h2 className="text-2xl sm:text-3xl font-bold text-foreground font-[family-name:var(--font-playfair)]">
                      Notre Mission
                    </h2>
                  </div>
                </div>
                <p className="text-muted leading-relaxed text-base sm:text-lg mb-4">
                  Flashback Restore est né d&apos;une conviction simple :{" "}
                  <strong className="text-foreground">
                    les souvenirs méritent d&apos;être préservés
                  </strong>
                  . Nous avons vu trop de photos de famille s&apos;abîmer avec le
                  temps — déchirures, décoloration, pliures. Ces images sont
                  souvent les seuls témoins visuels de moments irremplaçables.
                </p>
                <p className="text-muted leading-relaxed text-base sm:text-lg">
                  En combinant les technologies d&apos;IA les plus avancées —
                  notre IA de restauration et notre technologie d&apos;animation —
                  nous permettons à chacun de redonner vie à ses photos anciennes
                  en quelques secondes, sans aucune compétence technique. Notre
                  plateforme est pensée pour être simple, rapide et respectueuse
                  de votre vie privée.
                </p>
              </div>
            </div>
          </motion.div>

          {/* Stats */}
          <motion.div
            {...fadeUp}
            className="mb-16"
          >
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {stats.map((stat, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.1 }}
                  className="bg-card border border-card-border rounded-2xl p-5 text-center hover:border-muted/50 transition-colors"
                >
                  <div className="text-2xl sm:text-3xl font-bold text-accent mb-1 font-[family-name:var(--font-playfair)]">
                    {stat.value}
                  </div>
                  <div className="text-muted text-xs sm:text-sm">
                    {stat.label}
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Values */}
          <motion.div
            variants={stagger}
            initial="initial"
            animate="animate"
            className="mb-16"
          >
            <motion.div variants={fadeUp} className="text-center mb-10">
              <h2 className="text-2xl sm:text-3xl font-bold text-foreground font-[family-name:var(--font-playfair)] mb-3">
                Nos <span className="text-gradient">Valeurs</span>
              </h2>
              <p className="text-muted">
                Ce qui guide chacune de nos décisions.
              </p>
            </motion.div>

            <div className="grid sm:grid-cols-2 gap-6">
              {values.map((value, i) => (
                <motion.div
                  key={i}
                  variants={fadeUp}
                  className="bg-card border border-card-border rounded-2xl p-6 hover:border-muted/50 transition-colors"
                >
                  <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center mb-4">
                    <value.icon className="w-5 h-5 text-accent" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground mb-2 font-[family-name:var(--font-playfair)]">
                    {value.title}
                  </h3>
                  <p className="text-muted leading-relaxed text-sm">
                    {value.description}
                  </p>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* How we're different */}
          <motion.div
            {...fadeUp}
            className="mb-16"
          >
            <div className="bg-card border border-card-border rounded-2xl p-6 sm:p-8">
              <h2 className="text-2xl font-bold text-foreground mb-6 font-[family-name:var(--font-playfair)] text-center">
                Pourquoi nous choisir ?
              </h2>
              <div className="grid sm:grid-cols-2 gap-4">
                {[
                  "Restauration IA de qualité professionnelle",
                  "Animation de portraits façon Harry Potter",
                  "Aucune compétence technique requise",
                  "Résultats en quelques secondes",
                  "Respect total de votre vie privée",
                  "Photos jamais conservées sans consentement",
                  "Interface simple et intuitive",
                  "Support client réactif 24/7",
                ].map((feature, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <div className="w-5 h-5 rounded-full bg-emerald-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <Check className="w-3 h-3 text-emerald-400" />
                    </div>
                    <span className="text-muted text-sm">{feature}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          {/* CTA */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="text-center p-8 sm:p-12 rounded-3xl bg-gradient-to-br from-accent/10 via-violet-500/5 to-transparent border border-card-border"
          >
            <Sparkles className="w-10 h-10 text-accent mx-auto mb-4" />
            <h2 className="text-2xl sm:text-3xl font-bold text-foreground mb-3 font-[family-name:var(--font-playfair)]">
              Prêt à redonner vie à vos souvenirs ?
            </h2>
            <p className="text-muted mb-6 max-w-md mx-auto">
              Essayez Flashback Restore gratuitement. Téléchargez une photo et
              découvrez la magie de l&apos;IA en quelques secondes.
            </p>
            <Link
              href="/upload"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-base hover:brightness-110 transition-all hover:shadow-xl hover:shadow-accent/30 active:scale-95"
            >
              <Sparkles className="w-5 h-5" />
              Restaurer une photo gratuitement
            </Link>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
