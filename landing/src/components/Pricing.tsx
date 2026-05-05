"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Check, Sparkles, Zap, Crown, Gift, Building2, Mail } from "lucide-react";

const plans = [
  {
    name: "Gratuit",
    icon: Gift,
    price: "0€",
    period: "à vie",
    description: "Pour découvrir la magie de Flashback Restore.",
    features: [
      "3 restaurations offertes",
      "0 animation",
      "Qualité standard",
      "Galerie de base",
    ],
    cta: "Commencer gratuitement",
    highlighted: false,
    gradient: "from-card-border/50 to-card/50",
    border: "border-card-border",
    buttonStyle:
      "border-2 border-card-border text-foreground hover:border-accent/30 hover:bg-surface transition-all",
  },
  {
    name: "Découverte",
    icon: Sparkles,
    price: "4,99€",
    period: "par mois",
    description: "Pour les amateurs de souvenirs. Le meilleur rapport qualité-prix.",
    features: [
      "10 restaurations / mois",
      "3 animations / mois",
      "Qualité HD",
      "Galerie cloud",
      "Sans filigrane",
      "Support par email",
    ],
    cta: "Essayer Découverte",
    highlighted: true,
    gradient: "from-amber-500/20 via-amber-400/10 to-violet-600/10",
    border: "border-accent/50",
    buttonStyle:
      "bg-accent text-white dark:text-gray-950 hover:brightness-110 shadow-xl shadow-accent/25 font-semibold",
    badge: "⭐ Le plus populaire",
  },
  {
    name: "Premium",
    icon: Crown,
    price: "29€",
    period: "par mois",
    description: "Pour les passionnés qui veulent le meilleur.",
    features: [
      "100 restaurations / mois",
      "30 animations / mois",
      "Qualité HD premium",
      "Galerie chiffrée cloud",
      "Sans filigrane",
      "Support prioritaire 24/7",
      "Colorisation automatique",
    ],
    cta: "Devenir Premium",
    highlighted: false,
    gradient: "from-violet-600/20 to-violet-500/5",
    border: "border-violet-500/20",
    buttonStyle:
      "border-2 border-violet-500/30 text-foreground hover:bg-violet-500/10 hover:border-violet-400 transition-all font-semibold",
  },
  {
    name: "Annuel",
    icon: Zap,
    price: "249€",
    period: "par an",
    description: "Tout le plan Premium avec 2 mois offerts.",
    features: [
      "100 restaurations / mois",
      "30 animations / mois",
      "Tous les avantages Premium",
      "2 mois offerts (99€ d'économies)",
      "Export vidéo HD",
      "Accès anticipé nouveautés",
      "Badge VIP communauté",
    ],
    cta: "S'abonner",
    highlighted: false,
    gradient: "from-emerald-600/20 to-emerald-500/5",
    border: "border-emerald-500/20",
    buttonStyle:
      "border-2 border-emerald-500/30 text-foreground hover:bg-emerald-500/10 hover:border-emerald-400 transition-all font-semibold",
    savings: "Économisez 99€",
  },
  {
    name: "Pro",
    icon: Building2,
    price: "Sur mesure",
    period: "",
    description: "Pour les professionnels : photographes, archives, musées.",
    features: [
      "Restaurations illimitées",
      "Animations illimitées",
      "Qualité maximale",
      "API dédiée",
      "Stockage prioritaire",
      "Support dédié 24/7",
      "Contrat SLA",
      "Formation équipe",
    ],
    cta: "Nous contacter",
    highlighted: false,
    gradient: "from-gray-500/10 to-gray-400/5",
    border: "border-gray-500/20",
    buttonStyle:
      "border-2 border-gray-500/30 text-foreground hover:bg-gray-500/10 hover:border-gray-400 transition-all font-semibold inline-flex items-center gap-2 justify-center",
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
  const isInView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.1 }}
      className={`relative ${
        plan.highlighted
          ? "scale-[1.03] lg:scale-105 z-10"
          : ""
      }`}
    >
      <div
        className={`relative bg-card rounded-2xl border ${plan.border} p-6 lg:p-8 flex flex-col h-full transition-all duration-300 ${
          plan.highlighted
            ? "shadow-2xl shadow-accent/10 dark:shadow-accent/5"
            : "hover:shadow-xl hover:shadow-black/10 dark:hover:shadow-black/30"
        } overflow-hidden`}
      >
        {/* Gradient bg */}
        <div
          className={`absolute inset-0 bg-gradient-to-br ${plan.gradient} opacity-60`}
        />

        {/* Badge */}
        {plan.badge && (
          <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-amber-400 to-amber-500 text-gray-950 text-xs font-bold rounded-full shadow-lg shadow-amber-500/25 whitespace-nowrap z-20">
            {plan.badge}
          </div>
        )}

        <div className="relative z-10 flex flex-col flex-1">
          {/* Header */}
          <div className="flex items-center gap-3 mb-4">
            <div
              className={`w-10 h-10 rounded-xl ${
                plan.highlighted ? "bg-accent/20" : "bg-surface"
              } flex items-center justify-center`}
            >
              <plan.icon
                className={`w-5 h-5 ${
                  plan.highlighted ? "text-accent" : "text-muted"
                }`}
              />
            </div>
            <span className="text-lg font-semibold text-foreground">
              {plan.name}
            </span>
          </div>

          {/* Price */}
          <div className="mb-2">
            <span className="text-4xl font-bold text-foreground">
              {plan.price}
            </span>
            {plan.period && (
              <span className="text-muted ml-2 text-sm">{plan.period}</span>
            )}
          </div>

          {/* Savings badge */}
          {plan.savings && (
            <span className="text-xs font-semibold text-emerald-500 bg-emerald-500/10 px-2.5 py-1 rounded-full w-fit mb-4 inline-flex items-center gap-1">
              <Zap className="w-3 h-3" />
              {plan.savings}
            </span>
          )}

          <p className="text-muted text-sm mb-6">{plan.description}</p>

          {/* Features */}
          <ul className="space-y-3 mb-8 flex-1">
            {plan.features.map((feature) => (
              <li key={feature} className="flex items-start gap-3">
                <Check
                  className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                    plan.highlighted ? "text-accent" : "text-emerald-500"
                  }`}
                />
                <span className="text-muted text-sm leading-tight">
                  {feature}
                </span>
              </li>
            ))}
          </ul>

          {/* CTA */}
          <button
            className={`w-full py-3.5 rounded-full text-sm transition-all active:scale-[0.97] ${plan.buttonStyle}`}
          >
            {plan.name === "Pro" && <Mail className="w-4 h-4" />}
            {plan.cta}
          </button>
        </div>
      </div>
    </motion.div>
  );
}

export default function Pricing() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section id="pricing" className="relative py-24 lg:py-32 bg-surface">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-accent text-sm font-semibold tracking-widest uppercase">
            Tarifs
          </span>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mt-4 mb-6 font-[family-name:var(--font-playfair)]">
            Choisissez votre
            <br />
            <span className="text-gradient">formule idéale</span>
          </h2>
          <p className="text-muted max-w-2xl mx-auto text-lg">
            Du gratuit au sur-mesure, il y a une formule pour chaque besoin.
            Sans engagement, annulez à tout moment.
          </p>
        </motion.div>

        {/* Cards — 5 columns on xl, 3 on md, 1 on mobile */}
        <div className="grid md:grid-cols-3 xl:grid-cols-5 gap-6 max-w-[90rem] mx-auto items-start">
          {plans.map((plan, index) => (
            <PricingCard key={plan.name} plan={plan} index={index} />
          ))}
        </div>

        {/* Bottom note */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="text-center text-muted/70 text-sm mt-10"
        >
          Tous les prix sont en euros TTC. Paiement sécurisé par Stripe.
        </motion.p>
      </div>
    </section>
  );
}
