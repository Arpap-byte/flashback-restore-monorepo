"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import Image from "next/image";
import {
  History, Image as ImageIcon, Sparkles, AlertTriangle,
  ExternalLink, Clock, Trash2, RotateCw, Video, ShieldCheck,
  Calendar, Download, ChevronDown, Wand2, Film, Upload, Camera,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useAuth } from "@/context/AuthContext";
import { useUser, useAuth as useClerkAuth } from "@clerk/nextjs";
import {
  getUserHistory, getPhotoUrl, getPhotoUrlAsync, TravailHistorique,
  deleteTravail, deleteAllHistory,
  getUserPreferences, updatePreferences,
  UserHistoryResponse
} from "@/lib/api";

const TYPE_LABELS: Record<string, string> = {
  analyse: "Analyse",
  restauration: "Restauration",
  animation: "Animation",
  colorisation: "Colorisation",
};

const TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  restauration: Sparkles,
  animation: Video,
  analyse: ImageIcon,
  colorisation: Sparkles,
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

const RETENTION_LABELS: Record<number, string> = {
  7: "7 jours",
  30: "30 jours",
  90: "3 mois",
};

function formatSize(octets: number | null): string {
  if (!octets) return "—";
  if (octets < 1024) return `${octets} o`;
  if (octets < 1024 * 1024) return `${(octets / 1024).toFixed(1)} Ko`;
  return `${(octets / (1024 * 1024)).toFixed(1)} Mo`;
}

function formatExpiration(iso: string | null): { text: string; urgent: boolean } {
  if (!iso) return { text: "—", urgent: false };
  const exp = new Date(iso);
  const now = new Date();
  const diffDays = Math.ceil((exp.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays <= 0) return { text: "Expiré", urgent: true };
  if (diffDays === 1) return { text: "Expire demain", urgent: true };
  if (diffDays <= 3) return { text: `${diffDays} jours`, urgent: true };
  if (diffDays <= 30) return { text: `${diffDays} jours`, urgent: false };
  return { text: `${Math.floor(diffDays / 30)} mois`, urgent: false };
}

export default function HistoriquePage() {
  const { user, loading: authLoading } = useAuth();
  const { user: clerkUser, isLoaded: clerkLoaded } = useUser();
  const { getToken } = useClerkAuth();
  const isAuthenticated = !!user || !!clerkUser;
  const [data, setData] = useState<UserHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [retentionOpen, setRetentionOpen] = useState(false);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"importees" | "retouchees" | "animations">("retouchees");

  // Récupérer le token JWT pour les URLs d'images (nécessaire car <img> ne peut pas envoyer de header Authorization)
  useEffect(() => {
    if (!isAuthenticated) return;
    getToken().then((t) => setAuthToken(t || null)).catch(() => setAuthToken(null));
  }, [isAuthenticated, getToken]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getUserHistory();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de chargement.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) return;
    fetchData();
  }, [user, authLoading, fetchData]);

  const handleDelete = async (travailId: string) => {
    setDeleting(travailId);
    try {
      await deleteTravail(travailId);
      await fetchData(); // refresh
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la suppression.");
    } finally {
      setDeleting(null);
    }
  };

  const handleDeleteAll = async () => {
    if (!confirmDeleteAll) {
      setConfirmDeleteAll(true);
      return;
    }
    setDeleting("__all__");
    try {
      await deleteAllHistory();
      setConfirmDeleteAll(false);
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la suppression.");
    } finally {
      setDeleting(null);
    }
  };

  const handleRetentionChange = async (jours: number) => {
    try {
      await updatePreferences(jours);
      setRetentionOpen(false);
      await fetchData(); // refresh to get new expire dates
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la mise à jour.");
    }
  };

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

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col min-h-screen bg-background">
        <Navbar />
        <main className="flex-1 pt-24 pb-16 flex items-center justify-center">
          <div className="text-center">
            <History className="w-16 h-16 text-muted mx-auto mb-4 opacity-50" />
            <h2 className="text-xl font-semibold text-foreground mb-2">
              Connectez-vous pour voir votre historique
            </h2>
            <p className="text-muted mb-6">Vos photos restaurées vous attendent.</p>
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

  const travaux = data?.travaux || [];
  const retention = data?.retention_jours || 30;

  // Filtrer + dédoublonner selon l'onglet actif
  const filteredTravaux = (() => {
    if (activeTab === "importees") {
      // Photos brutes : url_original des restaurations/colorisations, dédoublonnées
      const seen = new Set<string>();
      return travaux.filter((t) => {
        if (t.type === "animation") return false; // pas de photo brute pour les animations
        const key = t.url_original || "";
        if (!key || seen.has(key)) return false;
        seen.add(key);
        return true;
      });
    }
    if (activeTab === "retouchees") {
      return travaux.filter((t) =>
        (t.type === "restauration" || t.type === "colorisation") && t.statut === "termine"
      );
    }
    // animations
    return travaux.filter((t) => t.type === "animation");
  })();

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 pt-24 pb-16">
        {/* Background */}
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-violet-600/6 rounded-full blur-[120px]" />
          <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-accent/5 rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
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
          </motion.div>

          {/* Barre d'onglets */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-center mb-8"
          >
            <div className="inline-flex bg-card border border-card-border rounded-2xl p-1.5 gap-1">
              {([
                { key: "importees", label: "Importées", icon: Upload },
                { key: "retouchees", label: "Retouchées", icon: Sparkles },
                { key: "animations", label: "Animations", icon: Film },
              ] as const).map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => setActiveTab(key)}
                  className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    activeTab === key
                      ? "bg-accent text-white dark:text-gray-950 shadow-lg shadow-accent/20"
                      : "text-muted hover:text-foreground hover:bg-surface-alt"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>
          </motion.div>

          {/* Count */}
          {filteredTravaux.length > 0 && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center text-xs text-muted mb-4"
            >
              {filteredTravaux.length} élément{filteredTravaux.length > 1 ? "s" : ""}
            </motion.p>
          )}

          {/* Retention + Delete all bar */}
          {filteredTravaux.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 flex flex-wrap items-center justify-between gap-3"
            >
              {/* Retention selector */}
              <div className="relative">
                <button
                  onClick={() => setRetentionOpen(!retentionOpen)}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-card border border-card-border text-sm text-muted hover:text-accent hover:border-accent/30 transition-all"
                >
                  <ShieldCheck className="w-4 h-4" />
                  Conservation : {RETENTION_LABELS[retention] || `${retention} jours`}
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform ${retentionOpen ? "rotate-180" : ""}`} />
                </button>
                {retentionOpen && (
                  <div className="absolute top-full mt-1 left-0 bg-card border border-card-border rounded-xl shadow-xl p-1.5 z-20 min-w-[200px]">
                    <p className="text-xs text-muted px-3 py-2 pb-1">Durée de conservation</p>
                    {[7, 30, 90].map((j) => (
                      <button
                        key={j}
                        onClick={() => handleRetentionChange(j)}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all ${
                          retention === j
                            ? "bg-accent/10 text-accent font-medium"
                            : "text-muted hover:text-foreground hover:bg-surface"
                        }`}
                      >
                        <span className="font-medium">{RETENTION_LABELS[j]}</span>
                        <span className="text-xs text-muted ml-2">
                          {j === 7 ? "Suppression rapide" : j === 90 ? "Conservation longue" : "Standard"}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Delete all */}
              <div className="flex items-center gap-2">
                {confirmDeleteAll && (
                  <span className="text-xs text-red-400 font-medium">Confirmer ?</span>
                )}
                <button
                  onClick={handleDeleteAll}
                  disabled={deleting === "__all__"}
                  className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    confirmDeleteAll
                      ? "bg-red-500/15 text-red-400 border border-red-500/30 hover:bg-red-500/25"
                      : "bg-card border border-card-border text-muted hover:text-red-400 hover:border-red-500/20"
                  }`}
                >
                  {deleting === "__all__" ? (
                    <RotateCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                  {confirmDeleteAll ? "Tout supprimer" : "Vider l'historique"}
                </button>
                {confirmDeleteAll && (
                  <button
                    onClick={() => setConfirmDeleteAll(false)}
                    className="px-3 py-2 text-sm text-muted hover:text-foreground transition-colors"
                  >
                    Annuler
                  </button>
                )}
              </div>
            </motion.div>
          )}

          {/* Error */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-8 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3"
            >
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-400 text-sm">{error}</p>
            </motion.div>
          )}

          {/* Empty state */}
          {filteredTravaux.length === 0 ? (
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
              {filteredTravaux.map((t, i) => {
                const Icon = TYPE_ICONS[t.type] || ImageIcon;
                const expiration = formatExpiration(t.expire_le);
                // Choisir l'URL selon l'onglet
                const photoUrl = activeTab === "importees"
                  ? (t.url_original || null)
                  : activeTab === "retouchees"
                    ? (t.url_resultat || t.url_original || null)
                    : (t.url_animation || t.url_original || null);
                const hasResult = t.url_resultat && t.statut === "termine";
                const hasAnimation = t.url_animation && t.statut === "termine";
                const isDeleting = deleting === t.id;

                return (
                  <motion.div
                    key={t.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="bg-card border border-card-border rounded-2xl overflow-hidden hover:border-accent/30 transition-all group relative"
                  >
                    {/* Photo preview */}
                    {photoUrl && (
                      <div className="aspect-[4/3] bg-surface-alt overflow-hidden relative">
                        <Image
                          src={getPhotoUrl(photoUrl, authToken)}
                          alt={TYPE_LABELS[t.type] || t.type}
                          fill
                          unoptimized
                          className="object-cover group-hover:scale-105 transition-transform duration-500"
                          sizes="(max-width: 640px) 50vw, 33vw"
                        />
                        {/* Delete button overlay */}
                        <button
                          onClick={() => handleDelete(t.id)}
                          disabled={isDeleting}
                          className="absolute top-2 right-2 w-8 h-8 rounded-lg bg-black/50 backdrop-blur-sm flex items-center justify-center text-white/70 hover:text-red-400 hover:bg-black/70 opacity-0 group-hover:opacity-100 transition-all"
                          title="Supprimer"
                        >
                          {isDeleting ? (
                            <RotateCw className="w-4 h-4 animate-spin" />
                          ) : (
                            <Trash2 className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    )}

                    {/* Info */}
                    <div className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-accent bg-accent/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                          <Icon className="w-3 h-3" />
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

                      {/* Expiration */}
                      <div className={`flex items-center gap-1.5 text-xs mt-1.5 ${
                        expiration.urgent ? "text-amber-400" : "text-muted"
                      }`}>
                        <Calendar className="w-3 h-3" />
                        {expiration.text === "—" ? "—" : `Expire : ${expiration.text}`}
                      </div>

                      {/* File sizes */}
                      {(t.taille_original || t.taille_resultat) && (
                        <div className="flex items-center gap-1.5 text-xs text-muted mt-1">
                          <Download className="w-3 h-3" />
                          {formatSize((t.taille_original || 0) + (t.taille_resultat || 0))}
                        </div>
                      )}

                      {t.message_erreur && (
                        <p className="text-xs text-red-400 mt-2 truncate">{t.message_erreur}</p>
                      )}

                      {/* Action buttons */}
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {/* Importées : boutons Restaurer + Animer */}
                        {activeTab === "importees" && (
                          <>
                            <a
                              href={`/restore?photo=${encodeURIComponent(getPhotoUrl(t.url_original!, authToken))}`}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-accent/10 text-accent text-xs hover:bg-accent/20 transition-colors"
                            >
                              <Sparkles className="w-3 h-3" />
                              Restaurer
                            </a>
                            <button
                              onClick={async () => {
                                const url = await getPhotoUrlAsync(t.url_original!);
                                sessionStorage.setItem("flashback_photo", url);
                                window.location.href = "/animate";
                              }}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-violet-500/10 text-violet-400 text-xs hover:bg-violet-500/20 transition-colors"
                            >
                              <Film className="w-3 h-3" />
                              Animer
                            </button>
                          </>
                        )}

                        {/* Retouchées : Résultat + Animer + Coloriser */}
                        {activeTab === "retouchees" && (
                          <>
                            {hasResult && (
                              <a
                                href={getPhotoUrl(t.url_resultat!, authToken)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-accent/10 text-accent text-xs hover:bg-accent/20 transition-colors"
                              >
                                <ExternalLink className="w-3 h-3" />
                                Résultat
                              </a>
                            )}
                            <button
                              onClick={async () => {
                                const src = t.url_resultat || t.url_original;
                                if (src) {
                                  const url = await getPhotoUrlAsync(src);
                                  sessionStorage.setItem("flashback_photo", url);
                                }
                                window.location.href = "/animate";
                              }}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-violet-500/10 text-violet-400 text-xs hover:bg-violet-500/20 transition-colors"
                            >
                              <Film className="w-3 h-3" />
                              Animer
                            </button>
                            {t.type === "restauration" && (
                              <button
                                onClick={async () => {
                                  const src = t.url_resultat || t.url_original;
                                  if (src) {
                                    const url = await getPhotoUrlAsync(src);
                                    sessionStorage.setItem("flashback_photo", url);
                                  }
                                  window.location.href = "/restore?mode=colorize-only";
                                }}
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-400 text-xs hover:bg-amber-500/20 transition-colors"
                              >
                                <Wand2 className="w-3 h-3" />
                                Coloriser
                              </button>
                            )}
                          </>
                        )}

                        {/* Animations : Vidéo ou erreur */}
                        {activeTab === "animations" && (
                          <>
                            {hasAnimation && (
                              <a
                                href={getPhotoUrl(t.url_animation!, authToken)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-violet-500/10 text-violet-400 text-xs hover:bg-violet-500/20 transition-colors"
                              >
                                <Video className="w-3 h-3" />
                                Voir l'animation
                              </a>
                            )}
                            {t.url_original && (
                              <a
                                href={getPhotoUrl(t.url_original!, authToken)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface text-muted text-xs hover:text-foreground hover:bg-surface-alt transition-colors"
                              >
                                <ImageIcon className="w-3 h-3" />
                                Photo source
                              </a>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          )}

          {/* Summary footer */}
          {filteredTravaux.length > 0 && data && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center text-xs text-muted mt-8"
            >
              {data.total} travail{data.total > 1 ? "x" : ""} au total · Conservation : {RETENTION_LABELS[retention]} ·{" "}
              Les fichiers sont automatiquement supprimés après expiration.
            </motion.p>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
