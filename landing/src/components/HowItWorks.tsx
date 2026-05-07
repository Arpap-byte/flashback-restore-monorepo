"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Camera, Sparkles, Heart, ArrowRight } from "lucide-react";

const steps = [
  {
    number: "1",
    icon: Camera,
    title: "Prenez une photo",
    description:
      "Photographiez votre ancien cliché directement depuis l'application ou importez-le depuis votre galerie. Formats JPG, PNG, TIFF et HEIC supportés.",
    color: "from-amber-500 to-amber-600",
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
    text: "text-amber-500",
  },
  {
    number: "2",
    icon: Sparkles,
    title: "L'IA restaure et anime",
    description:
      "Notre IA de restauration corrige les défauts, notre IA d&apos;animation donne vie au portrait. En quelques secondes, votre photo ancienne devient une animation fluide et naturelle.",
    color: "from-violet-500 to-violet-600",
    bg: "bg-violet-500/10",
    border: "border-violet-500/20",
    text: "text-violet-400",
  },
  {
    number: "3",
    icon: Heart,
    title: "Partagez l'émotion",
    description:
      "Sauvegardez vos créations et partagez-les avec vos proches. Revivez ensemble les souvenirs qui comptent le plus pour vous.",
    color: "from-emerald-500 to-emerald-600",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
    text: "text-emerald-400",
  },
];

function StepCard({
  step,
  index,
  isLast,
}: {
  step: (typeof steps)[0];
  index: number;
  isLast: boolean;
}) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, x: -30 }}
      animate={isInView ? { opacity: 1, x: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.2 }}
      className="relative flex gap-6"
    >
      {/* Timeline */}
      <div className="flex flex-col items-center">
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          animate={isInView ? { scale: 1, rotate: 0 } : {}}
          transition={{ duration: 0.5, delay: index * 0.2 + 0.2, type: "spring" }}
          className={`relative w-14 h-14 rounded-2xl ${step.bg} ${step.border} border flex items-center justify-center flex-shrink-0 shadow-lg`}
        >
          <step.icon className={`w-7 h-7 ${step.text}`} />
          <span className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-accent text-white dark:text-gray-950 text-xs font-bold flex items-center justify-center shadow-md">
            {step.number}
          </span>
        </motion.div>
        {!isLast && (
          <div className="w-0.5 h-20 bg-gradient-to-b from-accent/40 to-transparent mt-2 rounded-full" />
        )}
      </div>

      <div className="pb-12">
        <h3 className="text-xl font-semibold text-foreground mb-3">
          {step.title}
        </h3>
        <p className="text-muted leading-relaxed max-w-md">
          {step.description}
        </p>
      </div>
    </motion.div>
  );
}

export default function HowItWorks() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section
      id="how-it-works"
      className="relative py-24 lg:py-32 bg-background"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          {/* Left: Steps */}
          <div>
            <motion.div
              ref={ref}
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6 }}
              className="mb-10"
            >
              <span className="text-accent text-sm font-semibold tracking-widest uppercase">
                Comment ça marche
              </span>
              <h2 className="text-3xl sm:text-4xl font-bold text-foreground mt-4 mb-6 font-[family-name:var(--font-playfair)]">
                Trois étapes,
                <br />
                <span className="text-gradient">des souvenirs ravivés</span>
              </h2>
              <p className="text-muted text-lg">
                Aucune compétence technique requise. Prenez une photo,
                laissez l&apos;IA faire le reste, et partagez le résultat avec
                ceux que vous aimez.
              </p>
            </motion.div>

            <div>
              {steps.map((step, index) => (
                <StepCard
                  key={step.number}
                  step={step}
                  index={index}
                  isLast={index === steps.length - 1}
                />
              ))}
            </div>
          </div>

          {/* Right: Illustration */}
          <motion.div
            initial={{ opacity: 0, x: 40 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="relative hidden lg:block"
          >
            <div className="relative rounded-3xl bg-card border border-card-border p-1 overflow-hidden shadow-2xl">
              {/* Phone mockup */}
              <div className="aspect-[9/16] max-w-[320px] mx-auto rounded-2xl bg-gradient-to-br from-surface via-surface-alt to-surface flex flex-col overflow-hidden">
                {/* Status bar */}
                <div className="px-4 py-3 flex items-center justify-between border-b border-card-border">
                  <span className="text-xs text-muted font-medium">
                    Flashback Restore
                  </span>
                  <Sparkles className="w-4 h-4 text-accent" />
                </div>

                {/* Content */}
                <div className="flex-1 flex items-center justify-center p-6">
                  <div className="text-center">
                    {/* Animated photo placeholder */}
                    <div className="w-40 h-48 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-amber-100/40 via-amber-200/20 to-amber-50/30 border-2 border-accent/20 flex items-center justify-center relative overflow-hidden shadow-lg">
                      <div className="text-6xl opacity-60">🖼️</div>
                      <motion.div
                        className="absolute inset-0 bg-gradient-to-t from-accent/20 to-transparent"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: [0, 0.4, 0] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      />
                      {/* Progress ring */}
                      <div className="absolute bottom-3 left-3 right-3">
                        <motion.div
                          className="h-1 rounded-full bg-accent/30 overflow-hidden"
                        >
                          <motion.div
                            className="h-full rounded-full bg-accent"
                            initial={{ width: "0%" }}
                            animate={isInView ? { width: "75%" } : {}}
                            transition={{ duration: 2, delay: 1 }}
                          />
                        </motion.div>
                      </div>
                    </div>

                    <p className="text-sm text-muted font-mono mb-4">
                      Analyse IA en cours...
                    </p>

                    {/* Steps indicators */}
                    <div className="space-y-2">
                      {["Détection des visages ✓", "Restauration en cours...", "Animation IA..."].map(
                        (label, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-2 text-xs text-muted"
                          >
                            <span
                              className={`w-2 h-2 rounded-full ${
                                i === 0
                                  ? "bg-emerald-500"
                                  : i === 1
                                  ? "bg-accent animate-pulse"
                                  : "bg-card-border"
                              }`}
                            />
                            {label}
                          </div>
                        )
                      )}
                    </div>
                  </div>
                </div>

                {/* Bottom bar */}
                <div className="px-4 py-3 border-t border-card-border flex items-center justify-center">
                  <span className="text-[10px] text-muted/60">
                    Propulsé par l&apos;intelligence artificielle
                  </span>
                </div>
              </div>
            </div>
            {/* Glow effect */}
            <div className="absolute -inset-8 bg-gradient-to-br from-accent/15 via-violet-500/8 to-transparent rounded-3xl blur-3xl -z-10" />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
