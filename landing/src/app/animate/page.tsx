"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import {
  Upload,
  Sparkles,
  AlertTriangle,
  X,
  Download,
  Play,
  RefreshCw,
  Film,
  MessageSquare,
  Clock,
  Check,
  Loader2,
  ExternalLink,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  animatePhoto,
  checkAnimationStatus,
  AnimationStatus,
} from "@/lib/api";

const POLL_TIMEOUT = 120_000; // 2 minutes max
const POLL_DELAYS = [5_000, 8_000, 12_000, 20_000]; // backoff exponentiel (5s → 8s → 12s → 20s)

const statusLabels: Record<string, string> = {
  en_attente: "En attente",
  en_cours: "En cours",
  termine: "Terminé",
  erreur: "Erreur",
};

export default function AnimatePage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [animating, setAnimating] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<AnimationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const pollAttempts = useRef(0);
  const pollStartTime = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // On mount, check for photo passed from restore page
  useEffect(() => {
    const stored = sessionStorage.getItem("flashback_photo");
    if (stored) {
      setPreview(stored);
      fetch(stored)
        .then((res) => res.blob())
        .then((blob) => {
          const f = new File([blob], "photo.jpg", { type: "image/jpeg" });
          setFile(f);
        })
        .catch(() => {});
    }
  }, []);

  // Polling avec timeout + backoff exponentiel
  useEffect(() => {
    if (!jobId || status?.status === "termine" || status?.status === "erreur")
      return;

    // Démarrer le chronomètre
    if (pollAttempts.current === 0) {
      pollStartTime.current = Date.now();
    }

    let cancelled = false;

    const poll = async () => {
      if (cancelled) return;

      const elapsed = Date.now() - pollStartTime.current;
      if (elapsed >= POLL_TIMEOUT) {
        setStatus({ status: "erreur", message: "L'animation a pris trop de temps. Veuillez réessayer." });
        return;
      }

      try {
        const result = await checkAnimationStatus(jobId);
        if (cancelled) return;
        setStatus(result);

        if (result.status === "termine" || result.status === "erreur") {
          return; // Arrêter le polling
        }

        // Planifier le prochain poll avec backoff
        const delay = POLL_DELAYS[Math.min(pollAttempts.current, POLL_DELAYS.length - 1)];
        pollAttempts.current += 1;
        pollRef.current = setTimeout(poll, delay);
      } catch (pollErr) {
        if (cancelled) return;
        console.error("Erreur de polling D-ID:", pollErr);
        // Continuer malgré l'erreur réseau — ne pas ignorer silencieusement
        const delay = POLL_DELAYS[Math.min(pollAttempts.current, POLL_DELAYS.length - 1)];
        pollAttempts.current += 1;
        pollRef.current = setTimeout(poll, delay);
      }
    };

    poll(); // premier poll immédiat

    return () => {
      cancelled = true;
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, [jobId, status?.status]);

  const handleFile = useCallback((f: File) => {
    const validTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!validTypes.includes(f.type)) {
      setError("Format non supporté. Utilisez JPG, PNG ou WebP.");
      setTimeout(() => setError(null), 6000);
      return;
    }
    if (f.size > 20 * 1024 * 1024) {
      setError("Fichier trop volumineux (max 20 Mo).");
      setTimeout(() => setError(null), 6000);
      return;
    }
    setError(null);
    setStatus(null);
    setJobId(null);
    setFile(f);
    const reader = new FileReader();
    reader.onloadend = () => setPreview(reader.result as string);
    reader.readAsDataURL(f);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const handleAnimate = async () => {
    if (!file) return;
    setAnimating(true);
    setError(null);
    setStatus({ status: "en_attente" });
    pollAttempts.current = 0;
    pollStartTime.current = 0;
    try {
      const result = await animatePhoto(file, text);
      setJobId(result.job_id);
      setStatus({ status: "en_cours" });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erreur lors du lancement de l'animation. Veuillez réessayer."
      );
      setStatus(null);
    } finally {
      setAnimating(false);
    }
  };

  const handleClear = () => {
    setFile(null);
    setPreview(null);
    setStatus(null);
    setJobId(null);
    setError(null);
    setSelectedPreset(null);
    setText("");
    pollAttempts.current = 0;
    pollStartTime.current = 0;
    sessionStorage.removeItem("flashback_photo");
    if (pollRef.current) clearTimeout(pollRef.current);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const progress =
    status?.progress ??
    (status?.status === "termine"
      ? 100
      : status?.status === "en_cours"
        ? 66
        : status?.status === "en_attente"
          ? 33
          : 0);

  const handleDownloadVideo = async (url: string) => {
    try {
      const res = await fetch(url);
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = "flashback-animation.mp4";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch {
      window.open(url, "_blank");
    }
  };

  // Auth check
  if (authLoading) {
    return (
      <div className="flex flex-col min-h-screen bg-background">
        <Navbar />
        <main className="flex-1 pt-24 pb-16 flex items-center justify-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="w-12 h-12 rounded-full border-2 border-violet-500/30 border-t-violet-500"
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
          <div className="text-center px-4">
            <Film className="w-16 h-16 text-muted mx-auto mb-4 opacity-50" />
            <h2 className="text-xl font-semibold text-foreground mb-2">
              Connectez-vous pour animer vos photos
            </h2>
            <p className="text-muted mb-6 max-w-md mx-auto">
              Transformez vos souvenirs en portraits animés avec notre
              technologie d&apos;animation.
            </p>
            <a
              href="/auth?callbackUrl=/animate"
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
        {/* Background glow */}
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/3 w-[600px] h-[600px] bg-violet-600/8 rounded-full blur-[120px]" />
          <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-accent/5 rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-12"
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-400 text-sm font-medium mb-6">
              <Film className="w-4 h-4" />
              Étape 3 — Animation
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              Donnez vie à
              <br />
              <span className="text-gradient">votre souvenir</span>
            </h1>
            <p className="text-muted text-lg max-w-xl mx-auto">
              Transformez votre photo restaurée en portrait animé. Comme dans
              Harry Potter, votre souvenir prend vie avec des expressions
              naturelles.
            </p>
          </motion.div>

          {/* Main content */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            {!preview ? (
              /* Upload zone */
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`relative rounded-3xl border-2 border-dashed p-12 lg:p-16 text-center cursor-pointer transition-all duration-300 ${
                  dragOver
                    ? "border-violet-400 bg-violet-500/5 scale-[1.01]"
                    : "border-card-border hover:border-muted bg-card/50"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleFile(f);
                  }}
                />
                <div className="flex flex-col items-center gap-4">
                  <motion.div
                    animate={dragOver ? { scale: 1.1, y: -4 } : {}}
                    className="w-20 h-20 rounded-2xl bg-violet-500/10 flex items-center justify-center"
                  >
                    <Film className="w-10 h-10 text-violet-400" />
                  </motion.div>
                  <div>
                    <p className="text-foreground text-lg font-semibold mb-1">
                      Glissez-déposez votre photo ici
                    </p>
                    <p className="text-muted text-sm">
                      ou cliquez pour parcourir vos fichiers
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="grid lg:grid-cols-5 gap-8">
                {/* Preview */}
                <div className="lg:col-span-2">
                  <div className="relative rounded-2xl overflow-hidden border border-card-border bg-card shadow-xl aspect-[3/4]">
                    <Image
                      src={preview}
                      alt="Aperçu de la photo"
                      fill
                      className="object-contain bg-surface-alt"
                      sizes="(max-width: 1024px) 100vw, 40vw"
                    />
                    {!animating && !status && (
                      <button
                        onClick={handleClear}
                        className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/50 backdrop-blur text-white flex items-center justify-center hover:bg-black/70 transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Right: Controls & Results */}
                <div className="lg:col-span-3 flex flex-col gap-6">
                  {!animating && !status && (
                    <>
                      {/* Preset animation choices */}
                      <div className="bg-card border border-card-border rounded-2xl p-6">
                        <div className="flex items-center gap-2 mb-3">
                          <Sparkles className="w-4 h-4 text-violet-400" />
                          <span className="text-sm font-semibold text-foreground">
                            Choisissez un style d&apos;animation
                          </span>
                        </div>
                        <p className="text-xs text-muted mb-4">
                          Notre IA donne vie à votre photo selon le style choisi.
                        </p>
                        <div className="flex flex-col gap-3">
                          {/* Option 1: Saluer et sourire */}
                          <button
                            onClick={() => {
                              setText("The person looks at the camera, raises their hand and waves hello with a warm, genuine smile spreading across their face. Their eyes crinkle naturally, and after the greeting they relax into a calm, content expression. The motion is smooth and lifelike — as if greeting an old friend.");
                              setSelectedPreset("wave");
                            }}
                            className={`w-full text-left p-4 rounded-xl border-2 transition-all duration-200 ${
                              selectedPreset === "wave"
                                ? "border-violet-500 bg-violet-500/10 shadow-lg shadow-violet-500/10"
                                : "border-card-border hover:border-violet-500/30 hover:bg-violet-500/5"
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl ${
                                selectedPreset === "wave"
                                  ? "bg-violet-500/20"
                                  : "bg-violet-500/10"
                              }`}>
                                👋
                              </div>
                              <div>
                                <p className="text-sm font-semibold text-foreground">
                                  Saluer et sourire
                                </p>
                                <p className="text-xs text-muted mt-0.5">
                                  La personne vous salue de la main avec un sourire chaleureux
                                </p>
                              </div>
                              {selectedPreset === "wave" && (
                                <Check className="w-5 h-5 text-violet-400 ml-auto flex-shrink-0" />
                              )}
                            </div>
                          </button>

                          {/* Option 2: Animer simplement */}
                          <button
                            onClick={() => {
                              setText("Subtle, natural facial animation: the person blinks gently, their head tilts ever so slightly, a soft smile appears and fades naturally. Their eyes have a lifelike sparkle, and small micro-expressions play across their face — as if they are truly alive and present in the moment, looking at you with quiet warmth.");
                              setSelectedPreset("natural");
                            }}
                            className={`w-full text-left p-4 rounded-xl border-2 transition-all duration-200 ${
                              selectedPreset === "natural"
                                ? "border-violet-500 bg-violet-500/10 shadow-lg shadow-violet-500/10"
                                : "border-card-border hover:border-violet-500/30 hover:bg-violet-500/5"
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl ${
                                selectedPreset === "natural"
                                  ? "bg-violet-500/20"
                                  : "bg-violet-500/10"
                              }`}>
                                ✨
                              </div>
                              <div>
                                <p className="text-sm font-semibold text-foreground">
                                  Animer simplement
                                </p>
                                <p className="text-xs text-muted mt-0.5">
                                  Mouvements subtils et naturels — clignement, sourire léger, présence vivante
                                </p>
                              </div>
                              {selectedPreset === "natural" && (
                                <Check className="w-5 h-5 text-violet-400 ml-auto flex-shrink-0" />
                              )}
                            </div>
                          </button>
                        </div>
                      </div>

                      {/* Info */}
                      <div className="bg-violet-500/5 border border-violet-500/10 rounded-xl p-4">
                        <p className="text-sm text-muted flex items-start gap-2">
                          <Sparkles className="w-4 h-4 text-violet-400 flex-shrink-0 mt-0.5" />
                          L&apos;animation utilise notre technologie pour créer un portrait
                          vivant avec des expressions faciales naturelles.
                          Résultat en vidéo MP4.
                        </p>
                      </div>

                      {/* Action */}
                      <button
                        onClick={handleAnimate}
                        disabled={!selectedPreset}
                        className={`w-full inline-flex items-center justify-center gap-2 px-6 py-4 rounded-full bg-gradient-to-r from-violet-500 to-violet-600 text-white font-semibold text-base transition-all active:scale-[0.97] ${
                          selectedPreset
                            ? "hover:brightness-110 hover:shadow-xl hover:shadow-violet-500/25"
                            : "opacity-50 cursor-not-allowed"
                        }`}
                      >
                        <Play className="w-5 h-5" />
                        Créer l&apos;animation
                      </button>
                    </>
                  )}

                  {/* Progress / Status */}
                  {status && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="space-y-6"
                    >
                      {/* Progress */}
                      <div className="bg-card border border-card-border rounded-2xl p-6">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="font-semibold text-foreground flex items-center gap-2">
                            {status.status === "termine" ? (
                              <Check className="w-5 h-5 text-emerald-400" />
                            ) : status.status === "erreur" ? (
                              <AlertTriangle className="w-5 h-5 text-red-400" />
                            ) : (
                              <Loader2 className="w-5 h-5 text-accent animate-spin" />
                            )}
                            {statusLabels[status.status] || status.status}
                          </h3>
                          <span className="text-sm text-muted">
                            {status.status === "termine"
                              ? "100%"
                              : progress + "%"}
                          </span>
                        </div>

                        {/* Progress bar */}
                        <div className="h-2 rounded-full bg-surface overflow-hidden mb-4">
                          <motion.div
                            className="h-full rounded-full bg-gradient-to-r from-violet-500 to-violet-400"
                            initial={{ width: 0 }}
                            animate={{ width: `${progress}%` }}
                            transition={{ duration: 0.5 }}
                          />
                        </div>

                        {/* Steps */}
                        <div className="flex items-center justify-between text-xs text-muted">
                          <span
                            className={
                              status.status !== "en_attente" &&
                              progress >= 33
                                ? "text-emerald-400"
                                : ""
                            }
                          >
                            Envoi
                          </span>
                          <span
                            className={
                              progress >= 66 ? "text-emerald-400" : ""
                            }
                          >
                            Traitement
                          </span>
                          <span
                            className={
                              progress >= 100 ? "text-emerald-400" : ""
                            }
                          >
                            Terminé
                          </span>
                        </div>
                      </div>

                      {/* Error state */}
                      {status.status === "erreur" && (
                        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                          <p className="text-red-400 text-sm">
                            {status.message ||
                              "Une erreur est survenue lors de l'animation. Veuillez réessayer."}
                          </p>
                          <button
                            onClick={handleClear}
                            className="mt-3 text-sm text-accent hover:underline"
                          >
                            Réessayer avec une autre photo
                          </button>
                        </div>
                      )}

                      {/* Result video */}
                      {status.status === "termine" && status.result_url && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.95 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className="space-y-4"
                        >
                          <div className="rounded-2xl overflow-hidden border border-card-border bg-card shadow-2xl">
                            <video
                              src={status.result_url}
                              controls
                              autoPlay
                              loop
                              className="w-full"
                              poster={preview || undefined}
                            />
                          </div>
                          <div className="flex flex-col sm:flex-row gap-3">
                            <button
                              onClick={() =>
                                status.result_url &&
                                handleDownloadVideo(status.result_url)
                              }
                              className="flex-1 inline-flex items-center justify-center gap-2 px-6 py-4 rounded-full bg-accent text-white dark:text-gray-950 font-semibold hover:brightness-110 transition-all hover:shadow-xl hover:shadow-accent/30 active:scale-[0.97]"
                            >
                              <Download className="w-5 h-5" />
                              Télécharger l&apos;animation
                            </button>
                            {status.result_url && (
                              <a
                                href={status.result_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center justify-center gap-2 px-6 py-4 rounded-full border border-card-border text-foreground hover:bg-card transition-all font-semibold"
                              >
                                <ExternalLink className="w-4 h-4" />
                                Ouvrir dans un nouvel onglet
                              </a>
                            )}
                            <button
                              onClick={handleClear}
                              className="flex items-center justify-center gap-2 px-6 py-4 rounded-full border border-card-border text-muted hover:text-foreground hover:border-muted transition-all"
                            >
                              <RefreshCw className="w-4 h-4" />
                              Nouvelle animation
                            </button>
                          </div>
                        </motion.div>
                      )}

                      {/* Waiting state - no video yet but not errored */}
                      {status.status !== "termine" &&
                        status.status !== "erreur" && (
                          <div className="text-center py-6">
                            <motion.div
                              animate={{ opacity: [0.5, 1, 0.5] }}
                              transition={{
                                duration: 2,
                                repeat: Infinity,
                              }}
                              className="text-muted text-sm"
                            >
                              L&apos;animation est en cours de création...
                              <br />
                              Cela peut prendre jusqu&apos;à 2 minutes.
                            </motion.div>
                          </div>
                        )}
                    </motion.div>
                  )}
                </div>
              </div>
            )}

            {/* Error toast */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  className="mt-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3"
                >
                  <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <p className="text-red-400 text-sm">{error}</p>
                  <button
                    onClick={() => setError(null)}
                    className="ml-auto text-red-400/60 hover:text-red-400"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
