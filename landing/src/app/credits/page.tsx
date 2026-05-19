"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Sparkles, ShoppingCart, Crown, Zap, Check, Loader2, ArrowRight } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { getCreditPacks, checkoutCreditPack, CreditPack } from "@/lib/api";

const PACK_LABELS: Record<string, { name: string; icon: React.ComponentType<{ className?: string }>; gradient: string }> = {
  S: { name: "Mini", icon: Zap, gradient: "from-emerald-500 to-teal-600" },
  M: { name: "Standard", icon: Sparkles, gradient: "from-blue-500 to-indigo-600" },
  L: { name: "Maxi", icon: Crown, gradient: "from-purple-500 to-pink-600" },
};

export default function CreditsPage() {
  const [packs, setPacks] = useState<CreditPack[]>([]);
  const [estAbonne, setEstAbonne] = useState(false);
  const [loading, setLoading] = useState(true);
  const [buying, setBuying] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getCreditPacks();
        setPacks(data.packs);
        setEstAbonne(data.est_abonne);
      } catch {
        setError("Impossible de charger les packs. Réessayez plus tard.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleBuy = async (code: string) => {
    setBuying(code);
    setError(null);
    try {
      const { url } = await checkoutCreditPack(code);
      window.location.href = url;
    } catch (e: any) {
      setError(e.message || "Erreur lors du paiement. Réessayez.");
      setBuying(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <main className="pt-24 lg:pt-32 pb-20 px-4">
          <div className="max-w-4xl mx-auto text-center">
            <div className="w-16 h-16 rounded-full border-4 border-accent/30 border-t-accent animate-spin mx-auto mb-6" />
            <p className="text-muted">Chargement des packs...</p>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-24 lg:pt-32 pb-20 px-4">
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 text-accent text-sm font-medium mb-4">
              <ShoppingCart className="w-4 h-4" />
              {estAbonne ? "Prix abonné — 25% de réduction" : "Achat ponctuel sans abonnement"}
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              Rechargez vos{" "}
              <span className="text-gradient">crédits</span>
            </h1>
            <p className="text-muted max-w-xl mx-auto">
              Achetez des crédits supplémentaires sans engagement. Utilisez-les quand vous voulez, ils n'expirent jamais.
            </p>
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-md mx-auto mb-8 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center"
            >
              {error}
            </motion.div>
          )}

          {/* Packs Grid */}
          {packs.length === 0 ? (
            <div className="text-center py-12 text-muted">
              <ShoppingCart className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>Aucun pack disponible pour le moment.</p>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {packs.map((pack, i) => {
                const meta = PACK_LABELS[pack.code] || { name: pack.code, icon: Zap, gradient: "from-accent to-accent/70" };
                const Icon = meta.icon;
                const prix = pack.prix_eur;
                const isRemise = pack.remise_abonne && prix < pack.prix_normal_eur;
                const prixParCredit = pack.credits > 0 ? (prix / pack.credits).toFixed(2) : "0";

                return (
                  <motion.div
                    key={pack.code}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1, duration: 0.3 }}
                    className={`relative bg-card border rounded-2xl p-6 flex flex-col transition-all hover:border-accent/30 hover:shadow-lg hover:shadow-accent/5 ${
                      i === packs.length - 1
                        ? "border-accent/40 ring-1 ring-accent/20 shadow-accent/5"
                        : "border-card-border"
                    }`}
                  >
                    {i === packs.length - 1 && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-accent text-white dark:text-gray-950 text-xs font-semibold">
                        Meilleure offre
                      </div>
                    )}

                    {/* Icon */}
                    <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${meta.gradient} flex items-center justify-center mb-4`}>
                      <Icon className="w-6 h-6 text-white" />
                    </div>

                    <h3 className="text-lg font-semibold text-foreground mb-1">{meta.name}</h3>
                    <p className="text-muted text-sm mb-4">{pack.credits} crédits</p>

                    {/* Price */}
                    <div className="mb-4">
                      <div className="flex items-baseline gap-1">
                        <span className="text-3xl font-bold text-foreground">{prix.toFixed(2).replace(".00", "")}€</span>
                        {isRemise && (
                          <span className="text-sm text-muted line-through">{pack.prix_normal_eur.toFixed(2).replace(".00", "")}€</span>
                        )}
                      </div>
                      <p className="text-muted/60 text-xs mt-1">{prixParCredit}€ / crédit</p>
                    </div>

                    {/* Features */}
                    <div className="space-y-2 mb-6 flex-1">
                      {[
                        `${pack.credits} crédits perpétuels`,
                        "Utilisation immédiate",
                        "Aucun engagement",
                      ].map((feature, j) => (
                        <div key={j} className="flex items-start gap-2 text-sm text-muted">
                          <Check className="w-4 h-4 text-green-400 mt-0.5 shrink-0" />
                          {feature}
                        </div>
                      ))}
                      {pack.remise_abonne && (
                        <div className="flex items-start gap-2 text-sm text-accent">
                          <Check className="w-4 h-4 text-accent mt-0.5 shrink-0" />
                          25% de remise abonné
                        </div>
                      )}
                    </div>

                    {/* Buy button */}
                    <button
                      onClick={() => handleBuy(pack.code)}
                      disabled={buying !== null}
                      className={`w-full py-3 rounded-xl font-semibold text-sm transition-all flex items-center justify-center gap-2 ${
                        i === packs.length - 1
                          ? "bg-accent text-white dark:text-gray-950 hover:brightness-110"
                          : "bg-surface border border-card-border text-foreground hover:bg-accent/10 hover:border-accent/30"
                      } disabled:opacity-50`}
                    >
                      {buying === pack.code ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <>
                          Acheter <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </button>
                  </motion.div>
                );
              })}
            </div>
          )}

          {/* Bottom CTA */}
          <div className="text-center mt-12">
            <p className="text-muted text-sm mb-4">Besoin de plus de crédits chaque mois ?</p>
            <Link
              href="/#pricing"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full border border-card-border text-foreground hover:bg-surface transition-all text-sm font-medium"
            >
              <Crown className="w-4 h-4" />
              Voir les abonnements
            </Link>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
