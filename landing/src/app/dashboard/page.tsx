"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import {
  LayoutDashboard,
  Sparkles,
  Image as ImageIcon,
  Play,
  CreditCard,
  Clock,
  Camera,
  ArrowRight,
  ExternalLink,
  AlertTriangle,
  RefreshCw,
  Crown,
  Zap,
  Gift,
  Briefcase,
  User,
  Calendar,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useAuth } from "@/context/AuthContext";
import {
  getUserHistory,
  getUserMe,
  getPhotoUrl,
  getUserPreferences,
  updatePreferences,
  TravailHistorique,
  UserMe,
} from "@/lib/api";

/* ------------------------------------------------------------------ */
/*  Constantes d'affichage des plans                                   */
/* ------------------------------------------------------------------ */

const PLAN_CONFIG: Record<
  string,
  {
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    bgClass: string;
    textClass: string;
    borderClass: string;
  }
> = {
  gratuit: {
    label: "Gratuit",
    icon: Gift,
    bgClass: "bg-muted/10",
    textClass: "text-muted",
    borderClass: "border-muted/20",
  },
  decouverte: {
    label: "Découverte",
    icon: Sparkles,
    bgClass: "bg-accent/10",
    textClass: "text-accent",
    borderClass: "border-accent/30",
  },
  premium: {
    label: "Premium",
    icon: Zap,
    bgClass: "bg-amber-500/10",
    textClass: "text-amber-400",
    borderClass: "border-amber-500/20",
  },
  annuel: {
    label: "Annuel",
    icon: Crown,
    bgClass: "bg-violet-500/10",
    textClass: "text-violet-400",
    borderClass: "border-violet-500/20",
  },
  pro: {
    label: "Pro",
    icon: Briefcase,
    bgClass: "bg-blue-500/10",
    textClass: "text-blue-400",
    borderClass: "border-blue-500/20",
  },
};

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

/* ------------------------------------------------------------------ */
/*  Animation variants                                                 */
/* ------------------------------------------------------------------ */

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: "easeOut" as const },
  },
};

const fadeIn = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

/* ------------------------------------------------------------------ */
/*  Skeleton loader                                                    */
/* ------------------------------------------------------------------ */

function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-xl bg-surface/60 ${className}`}
    />
  );
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 pt-24 pb-16">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          {/* Header skeleton */}
          <div className="mb-10">
            <Skeleton className="h-8 w-64 mx-auto mb-4" />
            <Skeleton className="h-4 w-48 mx-auto" />
          </div>

          {/* Stats skeleton */}
          <div className="grid sm:grid-cols-3 gap-4 mb-10">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-card border border-card-border rounded-2xl p-6"
              >
                <Skeleton className="h-4 w-20 mb-3" />
                <Skeleton className="h-8 w-16 mb-2" />
                <Skeleton className="h-3 w-24" />
              </div>
            ))}
          </div>

          {/* Subscription + History skeleton */}
          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1 bg-card border border-card-border rounded-2xl p-6">
              <Skeleton className="h-5 w-32 mb-4" />
              <Skeleton className="h-10 w-full mb-3" />
              <Skeleton className="h-4 w-24" />
            </div>
            <div className="lg:col-span-2 bg-card border border-card-border rounded-2xl p-6">
              <Skeleton className="h-5 w-40 mb-4" />
              <Skeleton className="h-40 w-full" />
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Non-connecté / état vide                                           */
/* ------------------------------------------------------------------ */

function NotConnected() {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 pt-24 pb-16 flex items-center justify-center">
        <div className="text-center px-4">
          <LayoutDashboard className="w-16 h-16 text-muted mx-auto mb-4 opacity-50" />
          <h2 className="text-xl font-semibold text-foreground mb-2">
            Connectez-vous pour accéder à votre tableau de bord
          </h2>
          <p className="text-muted mb-6 max-w-md mx-auto">
            Suivez vos crédits, vos restaurations et gérez votre abonnement
            en un coup d&apos;œil.
          </p>
          <Link
            href="/auth"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold hover:brightness-110 transition-all"
          >
            Se connecter
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page principale                                                    */
/* ------------------------------------------------------------------ */

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth();

  // États
  const [userMe, setUserMe] = useState<UserMe | null>(null);
  const [travaux, setTravaux] = useState<TravailHistorique[]>([]);
  const [loadingData, setLoadingData] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retention, setRetention] = useState<number>(30);

  /* ---------- Récupération des données ---------- */

  const lastFetchedUserId = useRef<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoadingData(true);
    setError(null);
    try {
      const [meData, historyData, prefsData] = await Promise.allSettled([
        getUserMe(),
        getUserHistory(),
        getUserPreferences(),
      ]);

      if (meData.status === "fulfilled") {
        setUserMe(meData.value);
      } else {
        // Fallback : utiliser les données basiques du contexte
        if (user) {
          setUserMe({
            id: user.id,
            email: user.email,
            nom: null,
            plan: user.est_abonne ? "decouverte" : "gratuit",
            credits: user.credits,
            credits_utilises: 0,
            photos_restaurees_mois: 0,
            animations_creees: 0,
            animations_utilisees: 0,
            animations_limite: 0,
            date_renouvellement: null,
            est_abonne: user.est_abonne,
            essais_restants: user.essais_restants,
            retention_jours: 30,
            derniere_activite: null,
          });
        }
      }

      if (historyData.status === "fulfilled") {
        setTravaux(historyData.value.travaux.slice(0, 5));
      }
      if (prefsData.status === "fulfilled") {
        setRetention(prefsData.value.retention_jours);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erreur lors du chargement des données."
      );
    } finally {
      setLoadingData(false);
      lastFetchedUserId.current = user?.id ?? null;
    }
  }, [user]);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setLoadingData(false);
      lastFetchedUserId.current = null;
      return;
    }
    // Only fetch if the user changed (prevents re-fetch loops)
    if (lastFetchedUserId.current === user.id) return;
    fetchData();
  }, [user, authLoading, fetchData]);

  /* ---------- Helpers ---------- */

  const planConfig = userMe ? PLAN_CONFIG[userMe.plan] ?? PLAN_CONFIG.gratuit : PLAN_CONFIG.gratuit;

  const formatDate = (iso: string | null) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  };

  const formatDateShort = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const creditsDisplay = userMe
    ? userMe.plan === "pro"
      ? "Illimités"
      : `${Math.max(0, userMe.credits)} crédits`
    : "—";

  const trialsDisplay = userMe
    ? userMe.plan === "gratuit"
      ? `${Math.max(0, userMe.essais_restants)} essais`
      : null
    : null;

  /* ---------- Rendu conditionnel ---------- */

  if (authLoading || loadingData) return <DashboardSkeleton />;
  if (!user) return <NotConnected />;

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />

      <main className="flex-1 pt-24 pb-16">
        {/* ---- Fond décoratif ---- */}
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-violet-600/6 rounded-full blur-[120px]" />
          <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-accent/5 rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6">
          {/* ============================================================ */}
          {/*  HEADER                                                       */}
          {/* ============================================================ */}
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="mb-10"
          >
            <motion.div variants={itemVariants} className="text-center mb-2">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 border border-accent/20 text-accent text-sm font-medium mb-4">
                <LayoutDashboard className="w-4 h-4" />
                Tableau de bord
              </div>
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-3 font-[family-name:var(--font-playfair)]">
                Bonjour{" "}
                <span className="text-gradient">
                  {userMe?.nom || user.email.split("@")[0]}
                </span>
              </h1>
              <p className="text-muted">{user.email}</p>
            </motion.div>

            {/* Badge d'abonnement */}
            <motion.div
              variants={itemVariants}
              className="flex justify-center mt-4"
            >
              <span
                className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-semibold border ${planConfig.bgClass} ${planConfig.textClass} ${planConfig.borderClass}`}
              >
                <planConfig.icon className="w-4 h-4" />
                {planConfig.label}
              </span>
            </motion.div>
          </motion.div>

          {/* ============================================================ */}
          {/*  CARTES DE STATS                                              */}
          {/* ============================================================ */}
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10"
          >
            {/* Crédits restants */}
            <motion.div
              variants={itemVariants}
              className="group bg-card border border-card-border rounded-2xl p-5 sm:p-6 hover:border-accent/30 transition-all duration-300 hover:shadow-lg hover:shadow-accent/5"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-muted uppercase tracking-wider">
                  Crédits restants
                </span>
                <div className="w-9 h-9 rounded-xl bg-accent/10 flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                  <CreditCard className="w-4.5 h-4.5 text-accent" />
                </div>
              </div>
              <p className="text-2xl sm:text-3xl font-bold text-foreground mb-1">
                {creditsDisplay}
              </p>
              <p className="text-xs text-muted">
                {userMe?.plan === "pro"
                  ? "Accès illimité"
                  : "Crédits achetés"}
              </p>
              {trialsDisplay && (
                <p className="text-sm text-accent mt-1 font-medium">
                  + {trialsDisplay} gratuits
                </p>
              )}
            </motion.div>

            {/* Photos restaurées ce mois-ci */}
            <motion.div
              variants={itemVariants}
              className="group bg-card border border-card-border rounded-2xl p-5 sm:p-6 hover:border-accent/30 transition-all duration-300 hover:shadow-lg hover:shadow-accent/5"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-muted uppercase tracking-wider">
                  Photos restaurées
                </span>
                <div className="w-9 h-9 rounded-xl bg-emerald-500/10 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
                  <ImageIcon className="w-4.5 h-4.5 text-emerald-400" />
                </div>
              </div>
              <p className="text-2xl sm:text-3xl font-bold text-foreground mb-1">
                {userMe?.photos_restaurees_mois ?? 0}
              </p>
              <p className="text-xs text-muted">Ce mois-ci</p>
            </motion.div>

            {/* Animations créées */}
            <motion.div
              variants={itemVariants}
              className="group bg-card border border-card-border rounded-2xl p-5 sm:p-6 hover:border-accent/30 transition-all duration-300 hover:shadow-lg hover:shadow-accent/5"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-muted uppercase tracking-wider">
                  Animations créées
                </span>
                <div className="w-9 h-9 rounded-xl bg-violet-500/10 flex items-center justify-center group-hover:bg-violet-500/20 transition-colors">
                  <Play className="w-4.5 h-4.5 text-violet-400" />
                </div>
              </div>
              <p className="text-2xl sm:text-3xl font-bold text-foreground mb-1">
                {userMe?.animations_creees ?? 0}
              </p>
              <p className="text-xs text-muted">
                {userMe?.plan === "gratuit"
                  ? "Non disponible"
                  : userMe?.plan === "pro"
                  ? "Illimité"
                  : userMe?.animations_limite
                  ? `${userMe.animations_utilisees ?? userMe.animations_creees ?? 0} / ${userMe.animations_limite} ce mois`
                  : "Ce mois-ci"}
              </p>
            </motion.div>
          </motion.div>

          {/* ============================================================ */}
          {/*  ABONNEMENT + DERNIÈRES RESTAURATIONS                         */}
          {/* ============================================================ */}
          <div className="grid lg:grid-cols-3 gap-6 mb-10">
            {/* ---- Abonnement actuel ---- */}
            <motion.div
              variants={fadeIn}
              initial="hidden"
              animate="visible"
              className="lg:col-span-1 bg-card border border-card-border rounded-2xl p-6 relative overflow-hidden"
            >
              {/* Fond décoratif */}
              <div
                className={`absolute inset-0 bg-gradient-to-br ${planConfig.bgClass} opacity-30 pointer-events-none`}
              />

              <div className="relative z-10">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-9 h-9 rounded-xl bg-accent/10 flex items-center justify-center">
                    <Crown className="w-4.5 h-4.5 text-accent" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground">
                    Abonnement
                  </h3>
                </div>

                {/* Plan actuel */}
                <div
                  className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-semibold mb-4 border ${planConfig.bgClass} ${planConfig.textClass} ${planConfig.borderClass}`}
                >
                  <planConfig.icon className="w-4 h-4" />
                  {planConfig.label}
                </div>

                {/* Rétention */}
                <div className="flex items-center gap-2 text-sm text-muted mb-4">
                  <ShieldCheck className="w-4 h-4 text-accent/70" />
                  <span>
                    Conservation :{" "}
                    <span className="text-foreground font-medium">
                      {retention === 7 ? "7 jours" : retention === 90 ? "3 mois" : `${retention} jours`}
                    </span>
                  </span>
                </div>

                {/* Date de renouvellement */}
                {userMe?.date_renouvellement && (
                  <div className="flex items-center gap-2 text-sm text-muted mb-4">
                    <Calendar className="w-4 h-4" />
                    <span>
                      Renouvellement :{" "}
                      {formatDate(userMe.date_renouvellement)}
                    </span>
                  </div>
                )}

                {userMe?.plan === "gratuit" && (
                  <p className="text-sm text-muted mb-4">
                    Passez à un abonnement pour débloquer plus de
                    restaurations et d&apos;animations.
                  </p>
                )}

                {/* Bouton changer de plan */}
                <Link
                  href="/#pricing"
                  className="mt-2 w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-full border-2 border-card-border text-foreground hover:border-accent/30 hover:bg-surface transition-all text-sm font-medium"
                >
                  <RefreshCw className="w-4 h-4" />
                  {userMe?.plan === "gratuit"
                    ? "Passer à un abonnement"
                    : "Changer de plan"}
                </Link>
              </div>
            </motion.div>

            {/* ---- Dernières restaurations ---- */}
            <motion.div
              variants={fadeIn}
              initial="hidden"
              animate="visible"
              transition={{ delay: 0.1 }}
              className="lg:col-span-2 bg-card border border-card-border rounded-2xl p-6"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-9 h-9 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                    <Camera className="w-4.5 h-4.5 text-emerald-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground">
                    Dernières restaurations
                  </h3>
                </div>
                {travaux.length > 0 && (
                  <Link
                    href="/historique"
                    className="text-sm text-accent hover:underline flex items-center gap-1"
                  >
                    Tout voir
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                )}
              </div>

              {travaux.length === 0 ? (
                /* État vide */
                <div className="text-center py-10">
                  <ImageIcon className="w-12 h-12 text-muted mx-auto mb-3 opacity-40" />
                  <p className="text-muted text-sm mb-4">
                    Aucune restauration pour le moment.
                  </p>
                  <Link
                    href="/restore"
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-accent text-white dark:text-gray-950 text-sm font-semibold hover:brightness-110 transition-all"
                  >
                    <Sparkles className="w-4 h-4" />
                    Restaurer une photo
                  </Link>
                </div>
              ) : (
                /* Mini galerie */
                <div className="space-y-3">
                  {travaux.map((t, i) => (
                    <motion.div
                      key={t.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.06 }}
                      className="flex items-center gap-4 p-3 rounded-xl hover:bg-surface/50 transition-colors group/item"
                    >
                      {/* Miniature */}
                      {(t.url_resultat || t.url_original) ? (
                        <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-lg overflow-hidden bg-surface-alt flex-shrink-0 border border-card-border relative">
                          <Image
                            src={getPhotoUrl(
                              t.url_resultat || t.url_original!
                            )}
                            alt={TYPE_LABELS[t.type] || t.type}
                            fill
                            className="object-cover group-hover/item:scale-110 transition-transform duration-300"
                            sizes="56px"
                          />
                        </div>
                      ) : (
                        <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-lg bg-surface flex items-center justify-center flex-shrink-0 border border-card-border">
                          <ImageIcon className="w-5 h-5 text-muted" />
                        </div>
                      )}

                      {/* Infos */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-sm font-medium text-foreground truncate">
                            {TYPE_LABELS[t.type] || t.type}
                          </span>
                          <span
                            className={`text-xs font-medium ${
                              STATUT_COLORS[t.statut] || "text-muted"
                            }`}
                          >
                            {STATUT_LABELS[t.statut] || t.statut}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 text-xs text-muted">
                          <Clock className="w-3 h-3" />
                          {formatDateShort(t.cree_le)}
                        </div>
                      </div>

                      {/* Lien résultat */}
                      {t.url_resultat && t.statut === "termine" && (
                        <a
                          href={getPhotoUrl(t.url_resultat)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-shrink-0 w-8 h-8 rounded-lg bg-surface border border-card-border flex items-center justify-center text-muted hover:text-accent hover:border-accent/30 transition-all"
                          title="Voir le résultat"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          </div>

          {/* ============================================================ */}
          {/*  ACTIONS RAPIDES                                              */}
          {/* ============================================================ */}
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            <motion.div variants={itemVariants} className="text-center mb-6">
              <h3 className="text-lg font-semibold text-foreground">
                Actions rapides
              </h3>
            </motion.div>
            <motion.div
              variants={itemVariants}
              className="flex flex-col sm:flex-row items-center justify-center gap-4"
            >
              <Link
                href="/restore"
                className="group w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-base hover:brightness-110 transition-all hover:shadow-xl hover:shadow-accent/30 active:scale-[0.97]"
              >
                <Sparkles className="w-5 h-5" />
                Restaurer une photo
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                href="/animate"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 rounded-full border-2 border-violet-500/30 text-foreground hover:bg-violet-500/10 hover:border-violet-400 font-semibold text-base transition-all active:scale-[0.97]"
              >
                <Play className="w-5 h-5 text-violet-400" />
                Animer une photo
              </Link>
            </motion.div>
          </motion.div>

          {/* ============================================================ */}
          {/*  ERREUR                                                       */}
          {/* ============================================================ */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-8 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3"
            >
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
              <button
                onClick={fetchData}
                className="text-red-400/60 hover:text-red-400 transition-colors flex-shrink-0"
                title="Réessayer"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </motion.div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
