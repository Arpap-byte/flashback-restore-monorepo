"use client";

import { motion } from "framer-motion";
import {
  FileText,
  AlertTriangle,
  Shield,
  CreditCard,
  Ban,
  Gavel,
  ChevronRight,
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

const sections = [
  {
    icon: FileText,
    title: "1. Acceptation des conditions",
    content:
      "En accédant et en utilisant le Service Flashback Restore (le \"Service\"), accessible sur flashback-restore.com, vous acceptez d'être lié par les présentes Conditions Générales d'Utilisation (\"CGU\"). Si vous n'acceptez pas ces conditions, veuillez ne pas utiliser le Service. Nous nous réservons le droit de modifier ces CGU à tout moment. Les modifications entrent en vigueur dès leur publication. Votre utilisation continue du Service après modification vaut acceptation.",
  },
  {
    icon: FileText,
    title: "2. Description du Service",
    content:
      "Flashback Restore est un service de restauration et d'animation de photos par intelligence artificielle. Notre plateforme utilise des technologies d'IA avancées pour :",
    bullets: [
      "Restaurer des photos anciennes, endommagées ou de mauvaise qualité.",
      "Améliorer la résolution et la netteté des images.",
      "Coloriser des photos en noir et blanc.",
      "Animer des portraits pour créer des vidéos avec expressions faciales naturelles.",
    ],
    extra:
      "Le Service est fourni \"tel quel\" et nous ne garantissons pas que les résultats répondront exactement à vos attentes. La qualité de la restauration dépend de l'état de l'image source.",
  },
  {
    icon: AlertTriangle,
    title: "3. Obligations de l'utilisateur",
    content:
      "En utilisant Flashback Restore, vous vous engagez à respecter les règles suivantes :",
    bullets: [
      "Ne pas télécharger de contenu illégal, offensant, diffamatoire, pornographique, violent, haineux ou portant atteinte aux droits d'autrui.",
      "Ne pas utiliser le Service pour usurper l'identité d'une autre personne.",
      "Ne pas tenter de contourner les limitations techniques du Service, de pratiquer du reverse engineering ou d'extraire des données de manière automatisée.",
      "Être âgé d'au moins 13 ans (ou 16 ans dans certains pays de l'UE) pour utiliser le Service.",
      "Fournir des informations exactes et à jour lors de la création de votre compte.",
      "Être responsable du maintien de la confidentialité de vos identifiants de compte.",
    ],
  },
  {
    icon: Shield,
    title: "4. Propriété intellectuelle",
    content: "",
    bullets: [
      "Vos images : vous conservez l'intégralité des droits de propriété intellectuelle sur les photos que vous téléchargez. En utilisant notre Service, vous nous accordez une licence limitée, temporaire et révocable pour traiter vos images uniquement aux fins de fourniture du Service.",
      "Notre technologie : le code, les algorithmes, les modèles d'IA, la marque, le logo et l'interface de Flashback Restore restent notre propriété exclusive ou celle de nos concédants de licence. Toute reproduction ou utilisation non autorisée est interdite.",
      "Résultats de restauration : les images restaurées et animations générées vous appartiennent. Vous êtes libre de les utiliser à des fins personnelles ou commerciales.",
    ],
  },
  {
    icon: Ban,
    title: "5. Limitation de responsabilité",
    content:
      "Dans toute la mesure permise par la loi applicable, Flashback Restore et ses dirigeants, employés et affiliés ne pourront être tenus responsables :",
    bullets: [
      "Des dommages indirects, accessoires, spéciaux ou consécutifs résultant de l'utilisation ou de l'impossibilité d'utiliser le Service.",
      "De la perte de données, de revenus ou de bénéfices.",
      "Des résultats de restauration ne correspondant pas à vos attentes.",
      "Des interruptions de service, bugs ou indisponibilités temporaires.",
      "De tout préjudice résultant d'une utilisation non autorisée de votre compte.",
    ],
    extra:
      "Notre responsabilité totale, pour quelque cause que ce soit, est limitée au montant que vous avez payé pour le Service au cours des 12 derniers mois précédant l'incident, ou à 50 € si aucun paiement n'a été effectué.",
  },
  {
    icon: CreditCard,
    title: "6. Conditions de paiement",
    content: "",
    bullets: [
      "Les tarifs applicables sont ceux affichés sur notre page de tarification au moment de l'achat.",
      "Le paiement est traité de manière sécurisée par Stripe, notre prestataire de paiement. Nous ne stockons pas vos données bancaires.",
      "Les prix sont indiqués en euros (€), toutes taxes comprises (TTC) pour les résidents de l'UE.",
      "Les abonnements sont renouvelés automatiquement. Vous pouvez annuler à tout moment depuis votre compte ; l'annulation prendra effet à la fin de la période en cours.",
      "Nous offrons une garantie satisfait ou remboursé de 14 jours pour les achats ponctuels. Pour les abonnements, le premier paiement est remboursable sous 14 jours.",
    ],
  },
  {
    icon: Ban,
    title: "7. Résiliation du compte",
    content:
      "Nous nous réservons le droit de suspendre ou de résilier votre compte et votre accès au Service, sans préavis, en cas de violation de ces CGU, notamment en cas de téléchargement de contenu illégal, de fraude, ou d'utilisation abusive du Service. Vous pouvez également supprimer votre compte à tout moment depuis les paramètres de votre compte. En cas de résiliation, vos données seront traitées conformément à notre Politique de Confidentialité.",
  },
  {
    icon: Shield,
    title: "8. Services tiers",
    content:
      "Notre Service intègre des API et services tiers (services d'IA, Stripe). Nous ne sommes pas responsables de la disponibilité, des performances ou des conditions propres à ces services tiers. L'utilisation de ces services peut être soumise à leurs propres conditions générales.",
  },
  {
    icon: Gavel,
    title: "9. Droit applicable et juridiction",
    content:
      "Les présentes CGU sont régies par le droit français. Tout litige relatif à l'interprétation ou à l'exécution des présentes sera soumis à la compétence exclusive des tribunaux français. Conformément à la réglementation européenne, vous pouvez également recourir à la plateforme de règlement en ligne des litiges de la Commission européenne (ec.europa.eu/consumers/odr).",
  },
  {
    icon: FileText,
    title: "10. Contact",
    content:
      "Pour toute question concernant ces Conditions Générales d'Utilisation, vous pouvez nous contacter à :",
    contact: {
      email: "apexcyber.eu@gmail.com",
      label: "Contacter le support",
    },
  },
];

export default function TermsPage() {
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
              <Gavel className="w-4 h-4" />
              Mentions légales
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              Conditions Générales{" "}
              <span className="text-gradient">d&apos;Utilisation</span>
            </h1>
            <p className="text-muted text-lg max-w-xl mx-auto">
              Les règles qui encadrent l&apos;utilisation de Flashback Restore.
              Lisez-les attentivement avant d&apos;utiliser notre Service.
            </p>
            <p className="text-muted/60 text-sm mt-4">
              En vigueur depuis le 1er mai 2026
            </p>
          </motion.div>

          {/* Breadcrumb */}
          <motion.div {...fadeUp} className="mb-12">
            <div className="flex items-center gap-2 text-sm text-muted">
              <Link href="/" className="hover:text-accent transition-colors">
                Accueil
              </Link>
              <ChevronRight className="w-4 h-4" />
              <span className="text-foreground">Conditions d&apos;Utilisation</span>
            </div>
          </motion.div>

          {/* Acceptance highlight */}
          <motion.div
            {...fadeUp}
            className="mb-10 p-5 rounded-2xl bg-accent/5 border border-accent/20 flex items-start gap-3"
          >
            <AlertTriangle className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
            <p className="text-muted text-sm leading-relaxed">
              <strong className="text-foreground">Important :</strong> En
              utilisant Flashback Restore, vous acceptez l&apos;intégralité de
              ces conditions. Si vous n&apos;êtes pas d&apos;accord, veuillez ne
              pas utiliser notre Service.
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
                          <FileText className="w-4 h-4" />
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
              Une question sur ces conditions ?
            </h3>
            <p className="text-muted mb-4">
              Contactez-nous, nous vous répondrons rapidement.
            </p>
            <a
              href="mailto:apexcyber.eu@gmail.com"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold hover:brightness-110 transition-all hover:shadow-lg hover:shadow-accent/25"
            >
              <FileText className="w-4 h-4" />
              Contacter le support juridique
            </a>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
