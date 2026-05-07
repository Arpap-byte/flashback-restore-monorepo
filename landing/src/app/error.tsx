"use client";

import { useEffect } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, ArrowLeft, RefreshCw, Home } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Erreur de la page :", error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      {/* Background glow */}
      <div className="absolute top-1/3 left-1/4 w-[500px] h-[500px] bg-red-500/5 rounded-full blur-[130px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-accent/4 rounded-full blur-[100px] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 max-w-md w-full"
      >
        {/* Card */}
        <div className="relative bg-card rounded-2xl border border-card-border p-8 sm:p-10 text-center shadow-2xl shadow-black/10">
          {/* Icon */}
          <div className="mx-auto mb-6 w-16 h-16 rounded-2xl bg-red-500/10 flex items-center justify-center">
            <AlertTriangle className="w-8 h-8 text-red-400" />
          </div>

          <h1 className="text-xl sm:text-2xl font-bold text-foreground mb-3 font-[family-name:var(--font-playfair)]">
            Oups, une erreur est survenue
          </h1>

          <p className="text-muted leading-relaxed mb-2">
            Quelque chose s&apos;est mal passé lors du chargement de cette page.
          </p>

          {error.message && (
            <p className="text-xs text-muted/70 mb-6 bg-surface rounded-lg px-3 py-2 border border-card-border truncate">
              {error.message}
            </p>
          )}

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={reset}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-sm hover:brightness-110 transition-all hover:shadow-lg hover:shadow-accent/30 active:scale-[0.97] justify-center"
            >
              <RefreshCw className="w-4 h-4" />
              Réessayer
            </button>
            <a
              href="/"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full border border-card-border text-foreground font-semibold text-sm hover:bg-card transition-all hover:border-accent/30 active:scale-[0.97] justify-center"
            >
              <Home className="w-4 h-4" />
              Retour à l&apos;accueil
            </a>
          </div>
        </div>

        {/* Subtle accent bar */}
        <div className="mt-4 h-1 rounded-full bg-gradient-to-r from-red-500/30 via-accent/20 to-violet-500/20" />
      </motion.div>
    </div>
  );
}
