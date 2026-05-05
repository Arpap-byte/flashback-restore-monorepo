"use client";

import { useState, useRef } from "react";
import { motion, useInView, AnimatePresence } from "framer-motion";
import { ChevronDown, HelpCircle } from "lucide-react";

const faqs = [
  {
    question: "Comment fonctionne la restauration de photos ?",
    answer:
      "Notre IA analyse votre photo pour détecter automatiquement les défauts : rayures, taches, déchirures, décoloration. Elle reconstruit ensuite les zones endommagées en s'appuyant sur le contexte de l'image. Le processus prend quelques secondes et le résultat est souvent spectaculaire.",
  },
  {
    question: "Mes photos sont-elles conservées en sécurité ?",
    answer:
      "Absolument. Toutes vos photos sont stockées dans une galerie privée avec chiffrement de bout en bout. Nous ne partageons jamais vos données et vous gardez le contrôle total sur vos souvenirs. Vous pouvez supprimer vos photos à tout moment.",
  },
  {
    question: "Puis-je annuler mon abonnement à tout moment ?",
    answer:
      "Oui, totalement. Il n'y a aucun engagement. Vous pouvez annuler votre abonnement premium à tout moment depuis les paramètres de l'application. Vous conserverez l'accès aux fonctionnalités premium jusqu'à la fin de la période facturée.",
  },
  {
    question: "Quels types de photos sont compatibles ?",
    answer:
      "Flashback Restore prend en charge la plupart des formats : JPG, PNG, TIFF, HEIC et WebP. L'application fonctionne aussi bien avec des photos numérisées qu'avec des photos prises directement depuis votre téléphone. La taille maximale est de 50 Mo par image.",
  },
  {
    question: "L'animation fonctionne-t-elle sur toutes les photos ?",
    answer:
      "L'animation fonctionne particulièrement bien sur les portraits et les photos de personnes. Notre IA détecte automatiquement les visages et applique des mouvements naturels. Pour les photos sans visage (paysages, objets), l'animation sera plus subtile mais peut tout de même apporter une touche de vie.",
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
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className="border border-white/5 rounded-xl overflow-hidden hover:border-white/10 transition-colors"
    >
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-5 text-left hover:bg-white/[0.02] transition-colors"
      >
        <span className="text-white font-medium pr-4">{faq.question}</span>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.3 }}
        >
          <ChevronDown className="w-5 h-5 text-amber-400 flex-shrink-0" />
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
            <p className="px-5 pb-5 text-gray-400 leading-relaxed">
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
    <section id="faq" className="relative py-24 lg:py-32 bg-gray-950">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-violet-600/10 border border-violet-500/20 text-violet-400 text-sm font-medium mb-6">
            <HelpCircle className="w-4 h-4" />
            Questions fréquentes
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6">
            On répond à
            <br />
            <span className="text-gradient">vos questions</span>
          </h2>
          <p className="text-gray-400 text-lg">
            Vous avez d&apos;autres questions ? N&apos;hésitez pas à nous
            contacter.
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
