"use client";

import { useState, useRef } from "react";
import { motion, useInView, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { ChevronDown, HelpCircle } from "lucide-react";

const faqs = [
  {
    question: "Comment fonctionne la restauration de photos ?",
    answer:
      "Notre IA de restauration analyse votre photo pour détecter automatiquement les défauts : rayures, taches, déchirures, décoloration. Elle reconstruit ensuite les zones endommagées en s&apos;appuyant sur le contexte de l&apos;image. Le processus prend moins de 10 secondes.",
  },
  {
    question: "Mes photos sont-elles conservées en sécurité ?",
    answer:
      "Absolument. Toutes vos photos sont stockées dans une galerie privée avec chiffrement de bout en bout. Nous ne partageons jamais vos données. Vous pouvez supprimer vos photos définitivement à tout moment depuis l'application.",
  },
  {
    question: "Puis-je annuler mon abonnement à tout moment ?",
    answer:
      "Oui, sans aucun engagement. Vous pouvez annuler votre abonnement premium depuis les paramètres de l'application ou via votre compte App Store / Google Play. Vous conservez l'accès jusqu'à la fin de la période facturée.",
  },
  {
    question: "Quels types de photos sont compatibles ?",
    answer:
      "Flashback Restore prend en charge JPG, PNG, TIFF, HEIC et WebP. L'application fonctionne avec des photos numérisées ou prises directement depuis votre téléphone. Taille maximale : 50 Mo par image.",
  },
  {
    question: "L'animation fonctionne-t-elle sur toutes les photos ?",
    answer:
      "L&apos;animation IA est optimisée pour les portraits de personnes. L&apos;IA détecte les visages et applique des expressions naturelles. Attention : pour des raisons de sécurité, notre IA d&apos;animation n&apos;accepte pas les photos contenant des enfants. Les photos de paysages ou d&apos;objets sans visage ne sont pas adaptées à l&apos;animation.",
  },
  {
    question: "Mes photos sont-elles privées ? L&apos;entreprise y a-t-elle accès ?",
    answer:
      "Vos photos sont strictement privées. L&apos;équipe Flashback Restore n&apos;a aucun accès à vos images. Elles sont traitées automatiquement par notre IA puis supprimées selon votre politique de conservation. Nous ne pouvons pas voir, télécharger ou utiliser vos photos — c&apos;est une garantie fondamentale de notre service.",
  },
  {
    question: "Pouvez-vous restaurer des photos que j&apos;ai perdues ou supprimées ?",
    answer:
      "Non, nous ne pouvons pas restaurer des photos que vous avez perdues ou supprimées de votre appareil. Flashback Restore améliore la qualité des photos que vous possédez déjà, mais ne récupère pas de données perdues. Aucune demande de restauration de photos perdues ne pourra être traitée : nous ne conservons pas de copie de vos images.",
  },
  {
    question: "Quelle est la différence entre la restauration et l&apos;animation ?",
    answer:
      "Notre IA de restauration analyse, nettoie et répare vos photos anciennes. Notre IA d&apos;animation transforme vos portraits restaurés en vidéos animées avec des expressions faciales réalistes, comme les portraits magiques d&apos;Harry Potter.",
  },
];

function FAQItem({
  faq,
  index,
  isOpen,
  onToggle,
}: {
  faq: (typeof faqs)[0];
  index: number;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.4, delay: index * 0.08 }}
      className={`border rounded-xl overflow-hidden transition-all duration-300 ${
        isOpen
          ? "border-accent/30 bg-card shadow-lg"
          : "border-card-border bg-card hover:border-accent/20"
      }`}
    >
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-5 text-left transition-colors"
      >
        <span className="text-foreground font-medium pr-4">
          {faq.question}
        </span>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.3 }}
          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
            isOpen ? "bg-accent/10" : "bg-surface"
          }`}
        >
          <ChevronDown
            className={`w-4 h-4 ${
              isOpen ? "text-accent" : "text-muted"
            }`}
          />
        </motion.div>
      </button>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <p className="px-5 pb-5 text-muted leading-relaxed">
              {faq.answer}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);
  const toggle = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section id="faq" className="relative py-24 lg:py-32 bg-surface">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-400 text-sm font-medium mb-6">
            <HelpCircle className="w-4 h-4" />
            Questions fréquentes
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-6 font-[family-name:var(--font-playfair)]">
            On répond à
            <br />
            <span className="text-gradient">vos questions</span>
          </h2>
          <p className="text-muted text-lg">
            Vous ne trouvez pas votre réponse ?{" "}
            <Link href="/#cta" className="text-accent hover:underline">
              Contactez-nous
            </Link>
          </p>
        </motion.div>

        <div className="space-y-3">
          {faqs.map((faq, index) => (
            <FAQItem
              key={index}
              faq={faq}
              index={index}
              isOpen={openIndex === index}
              onToggle={() => toggle(index)}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
