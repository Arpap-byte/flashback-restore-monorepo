"use client";

import { motion } from "framer-motion";
import { AlertTriangle, ArrowRight, Gift } from "lucide-react";
import Link from "next/link";

interface OutOfCreditsModalProps {
  onClose: () => void;
  redirectPath?: string;
}

export default function OutOfCreditsModal({ onClose, redirectPath = "/#pricing" }: OutOfCreditsModalProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0, y: 20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        transition={{ type: "spring", damping: 20, stiffness: 260 }}
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-md rounded-2xl bg-surface border border-red-500/20 shadow-2xl overflow-hidden"
      >
        {/* Gradient band on top */}
        <div className="h-1.5 bg-gradient-to-r from-red-500 via-amber-500 to-red-500" />

        <div className="p-6">
          {/* Icon */}
          <div className="mx-auto w-14 h-14 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
            <AlertTriangle className="w-7 h-7 text-red-400" />
          </div>

          {/* Title */}
          <h2 className="text-xl font-bold text-center text-foreground mb-2">
            Plus de crédits disponibles
          </h2>

          {/* Description */}
          <p className="text-sm text-center text-muted mb-1">
            Vous avez utilisé tous vos essais gratuits et vous n&apos;avez
            plus de crédits.
          </p>
          <p className="text-sm text-center text-muted mb-6">
            Pour continuer à restaurer vos photos, passez à un
            abonnement premium.
          </p>

          {/* Features */}
          <div className="grid grid-cols-2 gap-2 mb-6">
            {[
              { icon: "🎬", text: "Animations HD" },
              { icon: "🎨", text: "Colorisation IA" },
              { icon: "📸", text: "Qualité 4K" },
              { icon: "☁️", text: "Galerie cloud" },
            ].map((f) => (
              <div
                key={f.text}
                className="flex items-center gap-2 p-2 rounded-lg bg-card border border-card-border"
              >
                <span className="text-sm">{f.icon}</span>
                <span className="text-xs text-foreground/80">{f.text}</span>
              </div>
            ))}
          </div>

          {/* CTA */}
          <Link
            href={redirectPath}
            className="w-full py-3.5 rounded-full bg-accent text-white font-semibold text-sm hover:brightness-110 transition-all active:scale-[0.97] inline-flex items-center justify-center gap-2 shadow-lg shadow-accent/25"
          >
            <Gift className="w-4 h-4" />
            Voir les offres
            <ArrowRight className="w-4 h-4" />
          </Link>

          {/* Later */}
          <button
            onClick={onClose}
            className="w-full mt-3 py-2.5 text-sm text-muted hover:text-foreground transition-colors"
          >
            Plus tard
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
