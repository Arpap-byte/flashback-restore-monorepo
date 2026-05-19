"use client";

import { motion } from "framer-motion";
import {
  Building2,
  Globe,
  Shield,
  Mail,
  ChevronRight,
  Scale,
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
  animate: { transition: { staggerChildren: 0.1 } },
};

export default function MentionsLegalesPage() {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 pt-28 pb-16">
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
              <Scale className="w-4 h-4" />
              Informations légales
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              Mentions{" "}
              <span className="text-gradient">Légales</span>
            </h1>
            <p className="text-muted text-lg max-w-xl mx-auto">
              Conformément aux dispositions des articles 6-III et 19 de la loi
              n°2004-575 du 21 juin 2004 pour la Confiance dans l&apos;économie
              numérique (LCEN).
            </p>
          </motion.div>

          {/* Breadcrumb */}
          <motion.div {...fadeUp} className="mb-12">
            <div className="flex items-center gap-2 text-sm text-muted">
              <Link href="/" className="hover:text-accent transition-colors">
                Accueil
              </Link>
              <ChevronRight className="w-4 h-4" />
              <span className="text-foreground">Mentions Légales</span>
            </div>
          </motion.div>

          <motion.div
            variants={stagger}
            initial="initial"
            animate="animate"
            className="space-y-8"
          >
            {/* Éditeur du site */}
            <motion.div
              variants={fadeUp}
              className="bg-card border border-card-border rounded-2xl p-6 sm:p-8"
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Building2 className="w-5 h-5 text-accent" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
                    Éditeur du site
                  </h3>
                  <div className="space-y-2 text-muted text-sm sm:text-base">
                    <p>
                      <strong className="text-foreground">Raison sociale :</strong>{" "}
                      APEX-CYBER
                    </p>
                    <p>
                      <strong className="text-foreground">Forme juridique :</strong>{" "}
                      Micro-entreprise / Entreprise individuelle
                    </p>
                    <p>
                      <strong className="text-foreground">Siège social :</strong>{" "}
                      [À compléter — adresse du siège]
                    </p>
                    <p>
                      <strong className="text-foreground">SIRET :</strong>{" "}
                      [À compléter — numéro SIRET]
                    </p>
                    <p>
                      <strong className="text-foreground">Capital social :</strong>{" "}
                      Non applicable (entreprise individuelle)
                    </p>
                    <p>
                      <strong className="text-foreground">N° TVA intracommunautaire :</strong>{" "}
                      [À compléter — FR + SIREN]
                    </p>
                    <p>
                      <strong className="text-foreground">Directeur de la publication :</strong>{" "}
                      Sébastien ARCHENY
                    </p>
                    <p>
                      <strong className="text-foreground">Contact :</strong>{" "}
                      <a
                        href="mailto:apexcyber.eu@gmail.com"
                        className="text-accent hover:underline"
                      >
                        apexcyber.eu@gmail.com
                      </a>
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Hébergement */}
            <motion.div
              variants={fadeUp}
              className="bg-card border border-card-border rounded-2xl p-6 sm:p-8"
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Globe className="w-5 h-5 text-accent" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
                    Hébergement
                  </h3>
                  <div className="space-y-2 text-muted text-sm sm:text-base">
                    <p>
                      <strong className="text-foreground">Hébergeur :</strong>{" "}
                      Hostinger International Ltd.
                    </p>
                    <p>
                      <strong className="text-foreground">Adresse :</strong>{" "}
                      61 Lordou Vironos Street, 6023 Larnaca, Chypre
                    </p>
                    <p>
                      <strong className="text-foreground">Site web :</strong>{" "}
                      <a
                        href="https://www.hostinger.fr"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-accent hover:underline"
                      >
                        www.hostinger.fr
                      </a>
                    </p>
                    <p className="mt-3 text-muted/70 text-xs">
                      Le site Flashback Restore est hébergé sur un serveur
                      privé virtuel (VPS) dédié situé dans un datacenter
                      européen.
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Propriété intellectuelle */}
            <motion.div
              variants={fadeUp}
              className="bg-card border border-card-border rounded-2xl p-6 sm:p-8"
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Shield className="w-5 h-5 text-accent" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
                    Propriété intellectuelle
                  </h3>
                  <p className="text-muted leading-relaxed text-sm sm:text-base">
                    L&apos;ensemble du site Flashback Restore (structure,
                    design, textes, images, logo, marque) est la propriété
                    exclusive d&apos;APEX-CYBER. Toute reproduction,
                    représentation, modification ou adaptation, totale ou
                    partielle, est interdite sans autorisation écrite
                    préalable.
                  </p>
                </div>
              </div>
            </motion.div>

            {/* Données personnelles / DPO */}
            <motion.div
              variants={fadeUp}
              className="bg-card border border-card-border rounded-2xl p-6 sm:p-8"
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Mail className="w-5 h-5 text-accent" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
                    Protection des données personnelles (RGPD)
                  </h3>
                  <div className="space-y-2 text-muted text-sm sm:text-base">
                    <p>
                      <strong className="text-foreground">
                        Responsable du traitement :
                      </strong>{" "}
                      Sébastien ARCHENY (APEX-CYBER)
                    </p>
                    <p>
                      <strong className="text-foreground">Contact DPO :</strong>{" "}
                      <a
                        href="mailto:apexcyber.eu@gmail.com"
                        className="text-accent hover:underline"
                      >
                        apexcyber.eu@gmail.com
                      </a>
                    </p>
                    <p className="mt-3">
                      Conformément au Règlement Général sur la Protection des
                      Données (RGPD) et à la loi Informatique et Libertés,
                      vous disposez d&apos;un droit d&apos;accès, de
                      rectification, d&apos;effacement, de limitation, de
                      portabilité et d&apos;opposition de vos données
                      personnelles.
                    </p>
                    <p>
                      Pour exercer ces droits, contactez-nous à l&apos;adresse
                      ci-dessus. Pour plus de détails, consultez notre{" "}
                      <Link
                        href="/privacy"
                        className="text-accent hover:underline"
                      >
                        Politique de Confidentialité
                      </Link>
                      .
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* CNIL */}
            <motion.div
              variants={fadeUp}
              className="bg-card border border-card-border rounded-2xl p-6 sm:p-8"
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Scale className="w-5 h-5 text-accent" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-foreground mb-3 font-[family-name:var(--font-playfair)]">
                    Droit applicable et médiation
                  </h3>
                  <p className="text-muted leading-relaxed text-sm sm:text-base">
                    En cas de litige non résolu, vous pouvez saisir la CNIL
                    (Commission Nationale de l&apos;Informatique et des
                    Libertés) — 3 Place de Fontenoy, 75007 Paris — ou recourir
                    à la plateforme de règlement en ligne des litiges de la
                    Commission européenne :{" "}
                    <a
                      href="https://ec.europa.eu/consumers/odr"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent hover:underline"
                    >
                      ec.europa.eu/consumers/odr
                    </a>
                  </p>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
