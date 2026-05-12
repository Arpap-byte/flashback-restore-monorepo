"use client";

import { motion } from "framer-motion";
import { XCircle, ArrowRight, Sparkles } from "lucide-react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export default function AbonnementAnnulationPage() {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 pt-28 pb-16 flex items-center justify-center">
        {/* Background glows */}
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/4 w-[700px] h-[700px] bg-amber-600/5 rounded-full blur-[130px]" />
          <div className="absolute bottom-1/3 right-1/4 w-[600px] h-[600px] bg-accent/4 rounded-full blur-[110px]" />
        </div>

        <div className="relative z-10 max-w-lg mx-auto px-4 sm:px-6 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="w-20 h-20 rounded-2xl bg-amber-500/10 flex items-center justify-center mx-auto mb-6">
              <XCircle className="w-10 h-10 text-amber-400" />
            </div>

            <h1 className="text-2xl sm:text-3xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              Paiement annulé
            </h1>

            <p className="text-muted text-lg mb-10 max-w-md mx-auto">
              Votre abonnement n&apos;a pas été débité. Vous pouvez explorer nos
              offres et choisir celle qui vous convient le mieux.
            </p>

            <Link
              href="/#pricing"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-base hover:brightness-110 transition-all hover:shadow-xl hover:shadow-accent/30 active:scale-[0.97]"
            >
              <Sparkles className="w-5 h-5" />
              Voir les offres
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
