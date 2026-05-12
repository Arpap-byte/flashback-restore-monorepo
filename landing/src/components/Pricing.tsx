"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Check, Sparkles, Zap, Crown, Gift, Briefcase } from "lucide-react";
import Link from "next/link";
import StripeCheckoutButton from "@/components/StripeCheckoutButton";

const plans = [
  {
    name: "Gratuit",
    icon: Gift,
    price: "0€",
    period: "à vie",
    description: "Pour découvrir la magie de Flashback Restore.",
    credits: "3 essais",
    features: [
      "3 essais gratuits",
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
    href: "/auth?mode=register",
  },
  {
    name: "Découverte",
    icon: Sparkles,
    price: "4,99€",
    period: "/mois",
    description: "Idéal pour débuter avec la restauration HD.",
    credits: "10 crédits/mois",
    features: [
      "10 restaurations HD/mois",
      "2 animations/mois",
      "Sans filigrane",
      "Galerie cloud",
      "Support email",
    ],
    cta: "S'abonner",
    highlighted: false,
    gradient: "from-amber-500/10 via-amber-400/5 to-violet-600/5",
    border: "border-card-border",
    buttonStyle:
      "border-2 border-card-border text-foreground hover:border-accent/30 hover:bg-surface transition-all",
    plan: "decouverte",
  },
  {
    name: "Premium",
    icon: Zap,
    price: "29€",
    period: "/mois",
    description: "Pour les passionnés de souvenirs.",
    credits: "100 crédits/mois",
    features: [
      "100 restaurations HD/mois",
      "25 animations/mois",
      "Sans filigrane",
      "Galerie cloud",
      "Support prioritaire",
    ],
    cta: "S'abonner",
    highlighted: true,
    gradient: "from-amber-500/20 via-amber-400/10 to-violet-600/10",
    border: "border-accent/50",
    buttonStyle:
      "bg-accent text-white dark:text-gray-950 hover:brightness-110 shadow-xl shadow-accent/25 font-semibold",
    badge: "⭐ Le plus populaire",
    plan: "premium",
  },
  {
    name: "Annuel",
    icon: Crown,
    price: "249€",
    period: "/an",
    description: "100 crédits/mois — 2 mois offerts !",
    credits: "100 crédits/mois",
    features: [
      "100 restaurations HD/mois",
      "25 animations/mois",
      "Sans filigrane",
      "Galerie cloud",
      "Support prioritaire",
      "Économisez 99€/an",
    ],
    cta: "S'abonner",
    highlighted: false,
    gradient: "from-violet-600/20 to-violet-500/5",
    border: "border-violet-500/20",
    buttonStyle:
      "border-2 border-violet-500/30 text-foreground hover:bg-violet-500/10 hover:border-violet-400 transition-all font-semibold",
    plan: "annuel",
    savings: "2 mois offerts",
  },
  {
    name: "Pro",
    icon: Briefcase,
    price: "Sur mesure",
    period: "",
    description: "Pour les studios, archives et gros volumes.",
    credits: "Crédits illimités",
    features: [
      "Crédits illimités",
      "Animations illimitées",
      "API dédiée",
      "Support 24/7",
      "Traitement par lot",
      "SLA garanti",
    ],
    cta: "Contactez-nous",
    highlighted: false,
    gradient: "from-blue-500/10 to-blue-400/5",
    border: "border-blue-500/20",
    buttonStyle:
      "border-2 border-blue-500/30 text-foreground hover:bg-blue-500/10 hover:border-blue-400 transition-all font-semibold",
    href: "mailto:contact@flashback-restore.fr",
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

  const renderCTA = () => {
    // Free plan → link to /upload
    if (plan.name === "Gratuit") {
      return (
        <Link
          href={plan.href || "/upload"}
          className={`w-full py-3.5 rounded-full text-sm transition-all active:scale-[0.97] inline-flex items-center justify-center gap-2 ${plan.buttonStyle}`}
        >
          {plan.cta}
        </Link>
      );
    }
    // Pro plan → mailto link
    if (plan.name === "Pro") {
      return (
        <a
          href={plan.href || "mailto:contact@flashback-restore.fr"}
          className={`w-full py-3.5 rounded-full text-sm transition-all active:scale-[0.97] inline-flex items-center justify-center gap-2 ${plan.buttonStyle}`}
        >
          {plan.cta}
        </a>
      );
    }
    // Subscription plans → Stripe checkout
    if (plan.plan) {
      return (
        <StripeCheckoutButton
          plan={plan.plan}
          label={plan.cta}
          className={plan.buttonStyle}
        />
      );
    }
    return null;
  };

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
      {/* Badge — outside overflow-hidden so it doesn't get clipped */}
      {plan.badge && (
        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-amber-400 to-amber-500 text-gray-950 text-xs font-bold rounded-full shadow-lg shadow-amber-500/25 whitespace-nowrap z-20">
          {plan.badge}
        </div>
      )}

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

        {/* Savings tag */}
        {plan.savings && (
          <div className="absolute top-4 right-4 px-3 py-1 bg-emerald-500/20 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs font-semibold rounded-full z-20">
            {plan.savings}
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
          <div className="mb-1">
            <span className="text-4xl font-bold text-foreground">
              {plan.price}
            </span>
            {plan.period && (
              <span className="text-muted ml-1 text-sm">{plan.period}</span>
            )}
          </div>

          {/* Credits highlight */}
          <div className="mb-2">
            <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${
              plan.highlighted
                ? "bg-accent/15 text-accent"
                : "bg-surface text-muted"
            }`}>
              {plan.credits}
            </span>
          </div>

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
          {renderCTA()}
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
            <span className="text-gradient">abonnement</span>
          </h2>
          <p className="text-muted max-w-2xl mx-auto text-lg">
            Des abonnements flexibles avec crédits mensuels. 
            Résiliez à tout moment, sans engagement.
          </p>
        </motion.div>

        {/* Cards — 5 columns on xl, 3 on lg, 2 on md, 1 on mobile */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6 max-w-[90rem] mx-auto items-start">
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
          Tous les prix sont en euros TTC. Paiement sécurisé par Stripe. Abonnement sans engagement, résiliez à tout moment.
        </motion.p>
      </div>
    </section>
  );
}
