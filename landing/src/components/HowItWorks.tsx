"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Camera, Sparkles, Share2, ArrowRight } from "lucide-react";

const steps = [
  {
    number: "01",
    icon: Camera,
    title: "Prenez une photo",
    description:
      "Photographiez votre ancien cliché directement depuis l'application ou importez-le depuis votre galerie. Formats JPG, PNG et TIFF acceptés.",
  },
  {
    number: "02",
    icon: Sparkles,
    title: "L'IA opère sa magie",
    description:
      "Notre intelligence artificielle analyse, restaure et anime votre photo en quelques secondes. Rayures, déchirures et couleurs sont corrigées automatiquement.",
  },
  {
    number: "03",
    icon: Share2,
    title: "Partagez vos souvenirs",
    description:
      "Sauvegardez vos créations dans votre galerie privée et partagez-les avec votre famille. Revivez ensemble les moments précieux du passé.",
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
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, x: -30 }}
      animate={isInView ? { opacity: 1, x: 0 } : {}}
      transition={{ duration: 0.6, delay: index * 0.2 }}
      className="relative flex gap-6"
    >
      {/* Timeline line */}
      <div className="flex flex-col items-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={isInView ? { scale: 1 } : {}}
          transition={{ duration: 0.4, delay: index * 0.2 + 0.2 }}
          className="w-14 h-14 rounded-2xl bg-amber-400/10 border border-amber-400/20 flex items-center justify-center flex-shrink-0"
        >
          <step.icon className="w-7 h-7 text-amber-400" />
        </motion.div>
        {!isLast && (
          <div className="w-px h-16 bg-gradient-to-b from-amber-400/30 to-transparent mt-2" />
        )}
      </div>

      <div className="pb-12">
        <span className="text-amber-400 text-sm font-bold tracking-widest">
          {step.number}
        </span>
        <h3 className="text-xl font-semibold text-white mt-2 mb-3">
          {step.title}
        </h3>
        <p className="text-gray-400 leading-relaxed max-w-md">
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
    <section id="how-it-works" className="relative py-24 lg:py-32 bg-gray-900">
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
              <span className="text-amber-400 text-sm font-semibold tracking-widest uppercase">
                Comment ça marche
              </span>
              <h2 className="text-3xl sm:text-4xl font-bold text-white mt-4 mb-6">
                Trois étapes,
                <br />
                <span className="text-gradient">des souvenirs ravivés</span>
              </h2>
              <p className="text-gray-400 text-lg">
                Aucune compétence technique requise. Laissez l&apos;IA faire le
                travail pendant que vous profitez du résultat.
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
            <div className="relative rounded-3xl bg-gray-800/50 border border-white/5 p-1 overflow-hidden">
              <div className="aspect-[3/4] rounded-2xl bg-gradient-to-br from-gray-800 via-gray-800/80 to-gray-900 flex items-center justify-center">
                <div className="text-center p-8">
                  <div className="w-32 h-32 mx-auto mb-6 rounded-full bg-amber-400/10 border border-amber-400/20 flex items-center justify-center">
                    <Sparkles className="w-16 h-16 text-amber-400 animate-pulse" />
                  </div>
                  <p className="text-gray-500 text-sm font-mono">
                    Analyse IA en cours...
                  </p>
                  <div className="mt-4 w-48 h-2 mx-auto rounded-full bg-gray-800 overflow-hidden">
                    <motion.div
                      className="h-full rounded-full bg-gradient-to-r from-amber-400 to-violet-600"
                      initial={{ width: "0%" }}
                      animate={isInView ? { width: "100%" } : {}}
                      transition={{ duration: 2, delay: 0.8 }}
                    />
                  </div>
                  <p className="text-gray-600 text-xs mt-4">
                    Restauration • Colorisation • Animation
                  </p>
                </div>
              </div>
            </div>
            {/* Glow effect */}
            <div className="absolute -inset-4 bg-gradient-to-br from-amber-400/10 via-violet-600/5 to-transparent rounded-3xl blur-2xl -z-10" />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
