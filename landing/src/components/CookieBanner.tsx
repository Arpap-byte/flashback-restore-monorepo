"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Cookie, Shield, X } from "lucide-react";
import Link from "next/link";

const COOKIE_CONSENT_KEY = "flashback_cookie_consent";

export default function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Ne pas afficher si déjà consenti
    if (localStorage.getItem(COOKIE_CONSENT_KEY)) return;
    // Afficher après un court délai
    const timer = setTimeout(() => setVisible(true), 500);
    return () => clearTimeout(timer);
  }, []);

  const acceptAll = () => {
    localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify({
      necessary: true,
      functional: true,
      date: new Date().toISOString(),
    }));
    setVisible(false);
  };

  const acceptNecessary = () => {
    localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify({
      necessary: true,
      functional: false,
      date: new Date().toISOString(),
    }));
    setVisible(false);
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 260 }}
          className="fixed bottom-0 left-0 right-0 z-50 p-3 sm:p-4"
        >
          <div className="max-w-3xl mx-auto bg-card/95 backdrop-blur-xl border border-card-border rounded-2xl p-4 sm:p-5 shadow-2xl shadow-black/20">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              {/* Icon */}
              <div className="hidden sm:flex w-10 h-10 rounded-full bg-accent/10 items-center justify-center flex-shrink-0">
                <Cookie className="w-5 h-5 text-accent" />
              </div>

              {/* Content */}
              <div className="flex-1">
                <p className="text-sm text-foreground leading-relaxed">
                  <span className="font-semibold">Respect de votre vie privée</span>
                  {" — "}
                  Nous utilisons des cookies strictement nécessaires au
                  fonctionnement du site (authentification, sécurité,
                  préférences). Avec votre accord, nous activons également
                  des cookies fonctionnels pour améliorer votre expérience.{" "}
                  <Link
                    href="/cookies"
                    className="text-accent hover:underline whitespace-nowrap"
                  >
                    En savoir plus
                  </Link>
                </p>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 flex-shrink-0 w-full sm:w-auto">
                <button
                  onClick={acceptNecessary}
                  className="flex-1 sm:flex-initial px-4 py-2.5 rounded-full border border-card-border text-sm text-muted hover:text-foreground hover:border-muted transition-all"
                >
                  Essentiels
                </button>
                <button
                  onClick={acceptAll}
                  className="flex-1 sm:flex-initial px-5 py-2.5 rounded-full bg-accent text-white text-sm font-semibold hover:brightness-110 transition-all active:scale-[0.97] shadow-md shadow-accent/20"
                >
                  Tout accepter
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
