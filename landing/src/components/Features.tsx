"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Sparkles, Film, Zap, Brain, Bot, Clock } from "lucide-react";

const features = [
  {
    icon: Brain,
    techIcon: Sparkles,
    title: "Restauration IA",
    tech: "IA de restauration",
    description:
      "Notre IA analyse et répare automatiquement les défauts de vos photos : rayures, déchirures, taches et couleurs délavées. Notre moteur de restauration détecte chaque imperfection et la corrige avec une précision bluffante.",
    gradient: "from-amber-500/20 to-amber-400/5",
    border: "border-amber-500/20",
    iconBg: "bg-amber-500/10",
    iconColor: "text-amber-500",
    techBg: "bg-amber-500/10",
    techColor: "text-amber-500",
  },
  {
    icon: Bot,
    techIcon: Film,
    title: "Animation magique",
    tech: "IA d&apos;animation",
    description:
      "Donnez vie à vos photos comme dans Harry Potter. Notre IA d&apos;animation transforme vos clichés en portraits animés avec des expressions naturelles : sourires, clignements, mouvements subtils. Un effet saisissant.",
    gradient: "from-violet-600/20 to-violet-500/5",
    border: "border-violet-500/20",
    iconBg: "bg-violet-500/10",
    iconColor: "text-violet-400",
    techBg: "bg-violet-500/10",
    techColor: "text-violet-400",
  },
  {
    icon: Zap,
    techIcon: Clock,
    title: "Simple & rapide",
    tech: "Instantané",
    description:
      "Prenez une photo ou importez-la, et en quelques secondes le résultat est là. Interface intuitive conçue pour tous les âges. Aucune compétence technique requise — la magie opère en un clic.",
    gradient: "from-emerald-500/20 to-emerald-400/5",
    border: "border-emerald-500/20",
    iconBg: "bg-emerald-500/10",
    iconColor: "text-emerald-400",
    techBg: "bg-emerald-500/10",
    techColor: "text-emerald-400",
  },
];

function FeatureCard({
  feature,
  index,
}: {
  feature: (typeof features)[0];
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
      className="group relative"
    >
      {/* Card */}
      <div
        className={`relative bg-card rounded-2xl border ${feature.border} p-8 h-full transition-all duration-300 hover:shadow-2xl hover:shadow-black/20 dark:hover:shadow-black/40 overflow-hidden`}
      >
        {/* Gradient background on hover */}
        <div
          className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500`}
        />

        <div className="relative z-10 flex flex-col h-full">
          {/* Icon + Tech badge */}
          <div className="flex items-start justify-between mb-6">
            <div
              className={`w-14 h-14 rounded-2xl ${feature.iconBg} flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-lg shadow-black/5`}
            >
              <feature.icon className={`w-7 h-7 ${feature.iconColor}`} />
            </div>
            <div
              className={`flex items-center gap-1.5 px-3 py-1 rounded-full ${feature.techBg} ${feature.techColor} text-xs font-semibold`}
            >
              <feature.techIcon className="w-3.5 h-3.5" />
              {feature.tech}
            </div>
          </div>

          <h3 className="text-xl font-semibold text-foreground mb-3">
            {feature.title}
          </h3>
          <p className="text-muted leading-relaxed flex-1">
            {feature.description}
          </p>

          {/* Bottom shimmer accent */}
          <div className="mt-6 h-1 rounded-full bg-surface overflow-hidden">
            <motion.div
              className={`h-full rounded-full bg-gradient-to-r ${feature.gradient.replace("/20","").replace("/5","")}`}
              initial={{ width: "0%" }}
              animate={isInView ? { width: "100%" } : {}}
              transition={{ duration: 0.8, delay: index * 0.15 + 0.3 }}
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default function Features() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section id="features" className="relative py-24 lg:py-32 bg-surface">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-accent text-sm font-semibold tracking-widest uppercase">
            Fonctionnalités
          </span>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mt-4 mb-6 font-[family-name:var(--font-playfair)]">
            Une technologie de pointe
            <br />
            <span className="text-gradient">au service de vos souvenirs</span>
          </h2>
          <p className="text-muted max-w-2xl mx-auto text-lg">
            Flashback Restore combine intelligence artificielle de pointe pour offrir une
            restauration et une animation d&apos;une qualité exceptionnelle,
            accessible à tous.
          </p>
        </motion.div>

        {/* Cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <FeatureCard key={feature.title} feature={feature} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}
