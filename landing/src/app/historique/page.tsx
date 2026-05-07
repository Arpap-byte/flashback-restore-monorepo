"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { History, Image as ImageIcon, Sparkles, AlertTriangle, ExternalLink, Clock } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useAuth } from "@/context/AuthContext";
import { getUserHistory, getPhotoUrl, TravailHistorique } from "@/lib/api";

const TYPE_LABELS: Record<string, string> = {
  analyse: "Analyse",
  restauration: "Restauration",
  animation: "Animation",
};

const STATUT_COLORS: Record<string, string> = {
  termine: "text-emerald-400",
  en_cours: "text-amber-400",
  erreur: "text-red-400",
  cree: "text-muted",
};

const STATUT_LABELS: Record<string, string> = {
  termine: "Terminé",
  en_cours: "En cours",
  erreur: "Erreur",
  cree: "Créé",
};

export default function HistoriquePage() {
  const { user, loading: authLoading } = useAuth();
  const [travaux, setTravaux] = useState<TravailHistorique[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!user) return;

    const fetchHistory = async () => {
      try {
        const data = await getUserHistory();
        setTravaux(data.travaux);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur de chargement.");
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [user, authLoading]);

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (authLoading || loading) {
    return (
      <div className="flex flex-col min-h-screen bg-background">
        <Navbar />
        <main className="flex-1 pt-24 pb-16 flex items-center justify-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="w-12 h-12 rounded-full border-2 border-accent/30 border-t-accent"
          />
        </main>
        <Footer />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex flex-col min-h-screen bg-background">
        <Navbar />
        <main className="flex-1 pt-24 pb-16 flex items-center justify-center">
          <div className="text-center">
            <History className="w-16 h-16 text-muted mx-auto mb-4 opacity-50" />
            <h2 className="text-xl font-semibold text-foreground mb-2">
              Connectez-vous pour voir votre historique
            </h2>
            <p className="text-muted mb-6">
              Vos photos restaurées vous attendent.
            </p>
            <a
              href="/auth"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold hover:brightness-110 transition-all"
            >
              Se connecter
            </a>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 pt-24 pb-16">
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-violet-600/6 rounded-full blur-[120px]" />
          <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-accent/5 rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-12"
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 border border-accent/20 text-accent text-sm font-medium mb-6">
              <History className="w-4 h-4" />
              Mon historique
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              Vos photos
              <br />
              <span className="text-gradient">restaurées</span>
            </h1>
            <p className="text-muted text-lg max-w-xl mx-auto">
              Retrouvez toutes vos photos analysées et restaurées.
            </p>
          </motion.div>

          {error && (
            <div className="mb-8 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {travaux.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-16"
            >
              <ImageIcon className="w-16 h-16 text-muted mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-semibold text-foreground mb-2">
                Aucune photo pour le moment
              </h3>
              <p className="text-muted mb-6">
                Restaurez votre première photo pour la voir apparaître ici.
              </p>
              <a
                href="/restore"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold hover:brightness-110 transition-all"
              >
                <Sparkles className="w-4 h-4" />
                Restaurer une photo
              </a>
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4"
            >
              {travaux.map((t, i) => (
                <motion.div
                  key={t.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="bg-card border border-card-border rounded-2xl overflow-hidden hover:border-accent/30 transition-all group"
                >
                  {/* Photo preview */}
                  {(t.chemin_resultat || t.chemin_photo) && (
                    <div className="aspect-[4/3] bg-surface-alt overflow-hidden relative">
                      <img
                        src={getPhotoUrl(t.chemin_resultat || t.chemin_photo!)}
                        alt={TYPE_LABELS[t.type] || t.type}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                    </div>
                  )}

                  {/* Info */}
                  <div className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-accent bg-accent/10 px-2 py-0.5 rounded-full">
                        {TYPE_LABELS[t.type] || t.type}
                      </span>
                      <span className={`text-xs font-medium ${STATUT_COLORS[t.statut] || "text-muted"}`}>
                        {STATUT_LABELS[t.statut] || t.statut}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 text-xs text-muted mt-2">
                      <Clock className="w-3 h-3" />
                      {formatDate(t.cree_le)}
                    </div>

                    {t.message_erreur && (
                      <p className="text-xs text-red-400 mt-2 truncate">
                        {t.message_erreur}
                      </p>
                    )}

                    {t.chemin_resultat && t.statut === "termine" && (
                      <a
                        href={getPhotoUrl(t.chemin_resultat)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-3 inline-flex items-center gap-1.5 text-xs text-accent hover:underline"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Voir le résultat
                      </a>
                    )}
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
