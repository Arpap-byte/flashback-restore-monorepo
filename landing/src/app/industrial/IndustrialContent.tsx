"use client";

import { motion } from "framer-motion";
import {
  Building2,
  Camera,
  Landmark,
  Users,
  Newspaper,
  Palette,
  GraduationCap,
  Heart,
  ChevronRight,
  Sparkles,
  Factory,
  Shield,
  Globe,
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

const industries = [
  {
    icon: Camera,
    title: "Photographie",
    description:
      "Les photographes professionnels utilisent Flashback Restore pour offrir un service de restauration à leurs clients. Retouchez les photos de mariage, portraits de famille et clichés argentiques avec une précision professionnelle.",
    benefits: [
      "Restauration de négatifs et tirages anciens",
      "Colorisation de photos noir et blanc",
      "Gain de temps sur les retouches manuelles",
    ],
  },
  {
    icon: Landmark,
    title: "Musées et archives",
    description:
      "Les institutions culturelles font confiance à notre IA pour préserver leur patrimoine visuel. Restaurez des documents historiques, des photographies d'archives et des œuvres fragiles sans les manipuler.",
    benefits: [
      "Préservation du patrimoine photographique",
      "Numérisation et restauration en masse",
      "Respect de l'intégrité des originaux",
    ],
  },
  {
    icon: Users,
    title: "Généalogie",
    description:
      "Les généalogistes et passionnés d'histoire familiale redonnent vie aux portraits de leurs ancêtres. Chaque photo restaurée devient un témoignage tangible pour les générations futures.",
    benefits: [
      "Restauration de photos de famille anciennes",
      "Animation de portraits d'ancêtres",
      "Partage facilité avec la famille",
    ],
  },
  {
    icon: Newspaper,
    title: "Presse et médias",
    description:
      "Les rédactions et agences de presse restaurent leurs archives photographiques pour illustrer des articles, documentaires et rétrospectives avec des images de qualité irréprochable.",
    benefits: [
      "Restauration rapide pour les bouclages",
      "Amélioration de la qualité des archives",
      "Traitement par lots pour les fonds importants",
    ],
  },
  {
    icon: Palette,
    title: "Mode et luxe",
    description:
      "Les maisons de mode et marques de luxe restaurent leurs catalogues et campagnes vintage. Redonnez leur éclat aux shootings historiques et aux archives de marque.",
    benefits: [
      "Restauration de catalogues vintage",
      "Colorisation fidèle des teintes d'époque",
      "Valorisation du patrimoine de marque",
    ],
  },
  {
    icon: GraduationCap,
    title: "Enseignement",
    description:
      "Les établissements scolaires et universités utilisent Flashback Restore pour leurs projets pédagogiques : restauration de photos historiques, travaux pratiques sur l'IA et documentation visuelle.",
    benefits: [
      "Support pédagogique pour cours d'histoire",
      "Projets étudiants en traitement d'image",
      "Documentation des archives scolaires",
    ],
  },
  {
    icon: Heart,
    title: "Santé et médico-social",
    description:
      "Les établissements de santé et EHPAD utilisent la restauration photo comme outil thérapeutique. Les photos de famille restaurées stimulent la mémoire et le bien-être émotionnel des résidents.",
    benefits: [
      "Thérapie par la réminiscence",
      "Activités intergénérationnelles",
      "Amélioration du bien-être des résidents",
    ],
  },
  {
    icon: Globe,
    title: "Tourisme et hôtellerie",
    description:
      "Les offices de tourisme et hôtels historiques restaurent leurs archives pour enrichir l'expérience visiteur. Mettez en valeur votre patrimoine avec des images d'époque sublimées.",
    benefits: [
      "Valorisation du patrimoine local",
      "Supports de communication enrichis",
      "Expérience visiteur immersive",
    ],
  },
];

const features = [
  {
    icon: Factory,
    title: "Traitement par lots",
    description:
      "Importez et restaurez jusqu'à 50 photos simultanément. Idéal pour les fonds d'archives volumineux et les projets de numérisation à grande échelle.",
  },
  {
    icon: Shield,
    title: "Sécurité et confidentialité",
    description:
      "Vos photos sont traitées de manière sécurisée et ne sont jamais conservées sans votre consentement. Conformité RGPD intégrale pour les professionnels.",
  },
  {
    icon: Sparkles,
    title: "Qualité professionnelle",
    description:
      "Notre IA produit des restaurations d'une qualité exceptionnelle, avec un niveau de détail et de fidélité qui satisfait les standards professionnels les plus exigeants.",
  },
];

export default function IndustrialContent() {
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
              <Building2 className="w-4 h-4" />
              Solutions sectorielles
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              Flashback Restore pour{" "}
              <span className="text-gradient">votre industrie</span>
            </h1>
            <p className="text-muted text-lg max-w-2xl mx-auto">
              Quel que soit votre secteur d'activité, notre intelligence
              artificielle s'adapte à vos besoins de restauration et
              d'animation de photos. Découvrez comment nous accompagnons
              les professionnels.
            </p>
          </motion.div>

          {/* Breadcrumb */}
          <motion.div {...fadeUp} className="mb-12">
            <div className="flex items-center gap-2 text-sm text-muted">
              <Link href="/" className="hover:text-accent transition-colors">
                Accueil
              </Link>
              <ChevronRight className="w-4 h-4" />
              <span className="text-foreground">Solutions par industrie</span>
            </div>
          </motion.div>

          {/* Industries grid */}
          <motion.div
            variants={stagger}
            initial="initial"
            animate="animate"
            className="mb-16"
          >
            <div className="grid sm:grid-cols-2 gap-6">
              {industries.map((industry, i) => (
                <motion.div
                  key={i}
                  variants={fadeUp}
                  className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-card to-surface border border-card-border p-6 sm:p-7 hover:border-accent/20 transition-all group"
                >
                  {/* Decorative blob */}
                  <div className="absolute top-0 right-0 w-32 h-32 bg-accent/5 rounded-full blur-[40px] -translate-y-1/2 translate-x-1/2 group-hover:bg-accent/10 transition-colors" />

                  <div className="relative">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0 group-hover:bg-accent/20 transition-colors">
                        <industry.icon className="w-5 h-5 text-accent" />
                      </div>
                      <h3 className="text-lg font-semibold text-foreground font-[family-name:var(--font-playfair)]">
                        {industry.title}
                      </h3>
                    </div>

                    <p className="text-muted text-sm leading-relaxed mb-4">
                      {industry.description}
                    </p>

                    <div className="space-y-2">
                      {industry.benefits.map((benefit, j) => (
                        <div
                          key={j}
                          className="flex items-start gap-2.5"
                        >
                          <div className="w-4 h-4 rounded-full bg-emerald-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <Check className="w-2.5 h-2.5 text-emerald-400" />
                          </div>
                          <span className="text-muted text-xs leading-relaxed">
                            {benefit}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Platform features */}
          <motion.div {...fadeUp} className="mb-16">
            <div className="text-center mb-10">
              <h2 className="text-2xl sm:text-3xl font-bold text-foreground font-[family-name:var(--font-playfair)] mb-3">
                Une plateforme pensée pour les{" "}
                <span className="text-gradient">professionnels</span>
              </h2>
              <p className="text-muted">
                Des fonctionnalités adaptées aux exigences des organisations.
              </p>
            </div>

            <div className="grid sm:grid-cols-3 gap-4">
              {features.map((feature, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.1 }}
                  className="bg-card border border-card-border rounded-2xl p-6 text-center hover:border-muted/50 transition-colors"
                >
                  <div className="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center mx-auto mb-4">
                    <feature.icon className="w-6 h-6 text-accent" />
                  </div>
                  <h3 className="text-foreground font-semibold mb-2 font-[family-name:var(--font-playfair)]">
                    {feature.title}
                  </h3>
                  <p className="text-muted text-sm leading-relaxed">
                    {feature.description}
                  </p>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Use case highlight */}
          <motion.div {...fadeUp} className="mb-16">
            <div className="relative rounded-3xl overflow-hidden bg-gradient-to-br from-accent/10 via-card to-violet-500/5 border border-card-border p-8 sm:p-12">
              <div className="absolute top-0 right-0 w-64 h-64 bg-accent/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2" />
              <div className="absolute bottom-0 left-0 w-48 h-48 bg-violet-500/10 rounded-full blur-[60px] translate-y-1/2 -translate-x-1/2" />

              <div className="relative">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-500 to-violet-600 flex items-center justify-center shadow-lg shadow-accent/25">
                    <Landmark className="w-7 h-7 text-white" />
                  </div>
                  <div>
                    <h2 className="text-2xl sm:text-3xl font-bold text-foreground font-[family-name:var(--font-playfair)]">
                      Cas d'usage : les archives municipales
                    </h2>
                  </div>
                </div>
                <p className="text-muted leading-relaxed text-base sm:text-lg mb-4">
                  Les services d'archives municipales gèrent des fonds
                  photographiques considérables, souvent endommagés par le
                  temps. Grâce à Flashback Restore, ils peuvent{" "}
                  <strong className="text-foreground">
                    numériser, restaurer et diffuser leur patrimoine
                  </strong>{" "}
                  auprès du public en quelques heures plutôt qu'en
                  plusieurs semaines.
                </p>
                <p className="text-muted leading-relaxed text-base sm:text-lg">
                  Notre solution de traitement par lots permet de restaurer des
                  centaines de clichés simultanément, tout en garantissant une
                  qualité muséale. Les fichiers restaurés sont livrés en haute
                  résolution, prêts pour l'archivage numérique et la
                  publication en ligne.
                </p>
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
              Vous avez un projet de restauration ?
            </h2>
            <p className="text-muted mb-6 max-w-md mx-auto">
              Contactez-nous pour découvrir comment Flashback Restore peut
              s'adapter à votre secteur d'activité et à vos volumes.
              Nous vous accompagnons de A à Z.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                href="/restore"
                className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-base hover:brightness-110 transition-all hover:shadow-xl hover:shadow-accent/30 active:scale-95"
              >
                <Sparkles className="w-5 h-5" />
                Essayer gratuitement
              </Link>
              <Link
                href="mailto:apexcyber.eu@gmail.com"
                className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full border border-card-border text-foreground hover:bg-surface font-medium text-base transition-all active:scale-95"
              >
                <Building2 className="w-5 h-5" />
                Contacter le service pro
              </Link>
            </div>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
