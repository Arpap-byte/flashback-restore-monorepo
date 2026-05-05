"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Apple, Play, Sparkles } from "lucide-react";

export default function CTASection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section id="cta" className="relative py-24 lg:py-32 bg-gray-900 overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-gradient-to-br from-amber-400/10 via-violet-600/10 to-transparent rounded-full blur-[120px]" />
      </div>

      <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 text-center">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-400/10 border border-amber-400/20 text-amber-400 text-sm font-medium mb-8">
            <Sparkles className="w-4 h-4" />
            Téléchargez l&apos;application
          </div>

          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6 leading-[1.2]">
            Prêt à redonner vie
            <br />
            <span className="text-gradient">à vos souvenirs ?</span>
          </h2>

          <p className="text-gray-400 max-w-xl mx-auto mb-10 text-lg">
            Téléchargez Flashback Restore dès maintenant et découvrez la magie
            de la restauration photo par IA. Vos souvenirs n&apos;attendent que
            vous.
          </p>

          {/* Store buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <a
              href="#"
              className="group inline-flex items-center gap-3 px-8 py-4 rounded-full bg-white text-gray-950 font-semibold hover:bg-gray-100 transition-all hover:shadow-xl hover:shadow-white/10 active:scale-95 w-full sm:w-auto justify-center"
            >
              <Apple className="w-6 h-6" />
              <div className="text-left">
                <div className="text-xs">Télécharger sur</div>
                <div className="text-base font-bold">App Store</div>
              </div>
            </a>
            <a
              href="#"
              className="group inline-flex items-center gap-3 px-8 py-4 rounded-full bg-white text-gray-950 font-semibold hover:bg-gray-100 transition-all hover:shadow-xl hover:shadow-white/10 active:scale-95 w-full sm:w-auto justify-center"
            >
              <Play className="w-6 h-6 fill-gray-950" />
              <div className="text-left">
                <div className="text-xs">Disponible sur</div>
                <div className="text-base font-bold">Google Play</div>
              </div>
            </a>
          </motion.div>

          {/* Bottom note */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ duration: 0.6, delay: 0.6 }}
            className="text-gray-600 text-sm mt-8"
          >
            Gratuit avec options premium. Aucune carte bancaire requise pour
            commencer.
          </motion.p>
        </motion.div>
      </div>
    </section>
  );
}
