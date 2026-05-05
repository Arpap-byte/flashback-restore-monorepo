"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Apple, Play, Sparkles, Shield, Star } from "lucide-react";

export default function CTASection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section
      id="cta"
      className="relative py-24 lg:py-32 bg-background overflow-hidden"
    >
      {/* Background */}
      <div className="absolute inset-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-br from-accent/15 via-violet-600/10 to-transparent rounded-full blur-[130px]" />
        <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-accent/5 rounded-full blur-[100px]" />
      </div>

      {/* Decorative top border */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-40 h-px bg-gradient-to-r from-transparent via-accent/40 to-transparent" />

      <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
        >
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 border border-accent/20 text-accent text-sm font-medium mb-8">
            <Sparkles className="w-4 h-4" />
            Disponible sur iOS et Android
          </div>

          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-6 leading-[1.2] font-[family-name:var(--font-playfair)]">
            Prêt à redonner vie
            <br />
            <span className="text-gradient">à vos souvenirs ?</span>
          </h2>

          <p className="text-muted max-w-xl mx-auto mb-10 text-lg">
            Téléchargez Flashback Restore et découvrez la magie de la
            restauration photo par IA. Vos souvenirs n&apos;attendent que vous.
          </p>

          {/* Store buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            {/* App Store */}
            <a
              href="/upload"
              className="group inline-flex items-center gap-3 px-8 py-4 rounded-2xl bg-foreground text-background font-semibold hover:opacity-90 transition-all hover:shadow-2xl hover:shadow-foreground/10 active:scale-[0.97] w-full sm:w-auto justify-center"
            >
              <Apple className="w-7 h-7" />
              <div className="text-left">
                <div className="text-xs opacity-70">Télécharger sur</div>
                <div className="text-base font-bold">App Store</div>
              </div>
            </a>

            {/* Google Play */}
            <a
              href="/upload"
              className="group inline-flex items-center gap-3 px-8 py-4 rounded-2xl bg-foreground text-background font-semibold hover:opacity-90 transition-all hover:shadow-2xl hover:shadow-foreground/10 active:scale-[0.97] w-full sm:w-auto justify-center"
            >
              <Play className="w-7 h-7 fill-background" />
              <div className="text-left">
                <div className="text-xs opacity-70">Disponible sur</div>
                <div className="text-base font-bold">Google Play</div>
              </div>
            </a>
          </motion.div>

          {/* Trust signals */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ duration: 0.6, delay: 0.6 }}
            className="flex flex-wrap items-center justify-center gap-6 mt-12 text-sm text-muted"
          >
            <span className="flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-emerald-500" />
              Paiement sécurisé
            </span>
            <span className="flex items-center gap-1.5">
              <Star className="w-4 h-4 fill-accent text-accent" />
              4.8 • 10K+ avis
            </span>
            <span className="text-muted/70">
              Formules dès 4,99€/mois — gratuit pour commencer
            </span>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
