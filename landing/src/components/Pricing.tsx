"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Check, Sparkles, Zap, Crown } from "lucide-react";

const plans = [
  {
    name: "Gratuit",
    icon: Zap,
    price: "0€",
    period: "à vie",
    description: "Pour découvrir la magie de Flashback Restore.",
    features: [
      "3 restaurations gratuites",
      "1 animation offerte",
      "Qualité standard",
      "Galerie de base",
      "Partage sur les réseaux",
    ],
    cta: "Commencer gratuitement",
    highlighted: false,
    gradient: "from-gray-700/50 to-gray-800/50",
    border: "border-white/10",
    buttonStyle: "border border-white/10 text-white hover:bg-white/5",
  },
  {
    name: "Premium",
    icon: Crown,
    price: "4,99€",
    period: "par mois",
    description: "Pour les passionnés de souvenirs.",
    features: [
      "Restaurations illimitées",
      "Animations illimitées",
      "Qualité HD premium",
      "Galerie chiffrée cloud",
      "Sans filigrane",
      "Support prioritaire",
      "Colorisation automatique",
    ],
    cta: "Essayer Premium",
    highlighted: true,
    gradient: "from-amber-400/20 via-amber-400/5 to-violet-600/10",
    border: "border-amber-400/40",
    buttonStyle:
      "bg-amber-400 text-gray-950 hover:bg-amber-300 shadow-lg shadow-amber-400/20",
    badge: "Le plus populaire",
  },
  {
    name: "Premium Annuel",
    icon: Sparkles,
    price: "39,99€",
    period: "par an",
    description: "Le meilleur rapport qualité-prix.",
    features: [
      "Tout le plan Premium",
      "2 mois offerts (33% d'économie)",
      "Animations 4K",
      "Export en vidéo HD",
      "Accès anticipé nouveautés",
      "Badge VIP communauté",
      "Sauvegarde prioritaire",
    ],
    cta: "Choisir l'annuel",
    highlighted: false,
    gradient: "from-violet-600/20 to-violet-600/5",
    border: "border-violet-500/20",
    buttonStyle:
      "border border-violet-400/30 text-white hover:bg-violet-600/10",
    savings: "Économisez 33%",
  },
];

function PricingCard({
  plan,
  index,
}: {
  plan: (typeof plans)[0];
  index: number;
}) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.15 }}
      className={`relative bg-gray-900 rounded-2xl border ${plan.border} p-8 flex flex-col ${
        plan.highlighted
          ? "scale-[1.02] lg:scale-105 shadow-2xl shadow-amber-400/5 z-10"
          : ""
      }`}
    >
      {/* Highlight badge */}
      {plan.badge && (
        <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-amber-400 to-amber-500 text-gray-950 text-xs font-bold rounded-full">
          {plan.badge}
        </div>
      )}

      {/* Gradient bg */}
      <div
        className={`absolute inset-0 bg-gradient-to-br ${plan.gradient} rounded-2xl opacity-50`}
      />

      <div className="relative z-10 flex flex-col flex-1">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div
            className={`w-10 h-10 rounded-xl ${
              plan.highlighted ? "bg-amber-400/20" : "bg-white/5"
            } flex items-center justify-center`}
          >
            <plan.icon
              className={`w-5 h-5 ${
                plan.highlighted ? "text-amber-400" : "text-gray-400"
              }`}
            />
          </div>
          <span className="text-lg font-semibold text-white">{plan.name}</span>
        </div>

        {/* Price */}
        <div className="mb-2">
          <span className="text-4xl font-bold text-white">{plan.price}</span>
          <span className="text-gray-500 ml-2">{plan.period}</span>
        </div>

        {/* Savings */}
        {plan.savings && (
          <span className="text-xs font-semibold text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full w-fit mb-4">
            {plan.savings}
          </span>
        )}

        <p className="text-gray-400 text-sm mb-6">{plan.description}</p>

        {/* Features */}
        <ul className="space-y-3 mb-8 flex-1">
          {plan.features.map((feature) => (
            <li key={feature} className="flex items-start gap-3">
              <Check
                className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                  plan.highlighted ? "text-amber-400" : "text-emerald-400"
                }`}
              />
              <span className="text-gray-300 text-sm">{feature}</span>
            </li>
          ))}
        </ul>

        {/* CTA */}
        <button
          className={`w-full py-3 rounded-full font-semibold text-sm transition-all active:scale-95 ${plan.buttonStyle}`}
        >
          {plan.cta}
        </button>
      </div>
    </motion.div>
  );
}

export default function Pricing() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section id="pricing" className="relative py-24 lg:py-32 bg-gray-950">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-amber-400 text-sm font-semibold tracking-widest uppercase">
            Tarifs
          </span>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mt-4 mb-6">
            Choisissez votre
            <br />
            <span className="text-gradient">formule idéale</span>
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto text-lg">
            Démarrez gratuitement et passez à la version premium quand vous le
            souhaitez. Pas d&apos;engagement, annulez à tout moment.
          </p>
        </motion.div>

        {/* Cards */}
        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {plans.map((plan, index) => (
            <PricingCard key={plan.name} plan={plan} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}
