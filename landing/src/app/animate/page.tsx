"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
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

const POLL_INTERVAL = 5000; // 5 seconds

const statusLabels: Record<string, string> = {
  en_attente: "En attente",
  en_cours: "En cours",
  termine: "Terminé",
  erreur: "Erreur",
};

export default function AnimatePage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [text, setText] = useState("Bonjour ! Je suis un souvenir restauré.");
  const [animating, setAnimating] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<AnimationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
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

  // Polling
  useEffect(() => {
    if (!jobId || status?.status === "termine" || status?.status === "erreur")
      return;

    const poll = async () => {
      try {
        const result = await checkAnimationStatus(jobId);
        setStatus(result);
        if (result.status === "termine" || result.status === "erreur") {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch {
        // Silently ignore polling errors
      }
    };

    poll(); // immediate first poll
    pollRef.current = setInterval(poll, POLL_INTERVAL);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobId, status?.status]);

  const handleFile = useCallback((f: File) => {
    const validTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!validTypes.includes(f.type)) {
      setError("Format non supporté. Utilisez JPG, PNG ou WebP.");
      return;
    }
    if (f.size > 20 * 1024 * 1024) {
      setError("Fichier trop volumineux (max 20 Mo).");
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
    sessionStorage.removeItem("flashback_photo");
    if (pollRef.current) clearInterval(pollRef.current);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const progress =
    status?.status === "termine"
      ? 100
      : status?.status === "en_cours"
        ? 66
        : status?.status === "en_attente"
          ? 33
          : 0;

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
                  <div className="relative rounded-2xl overflow-hidden border border-card-border bg-card shadow-xl">
                    <img
                      src={preview}
                      alt="Aperçu de la photo"
                      className="w-full aspect-[3/4] object-contain bg-surface-alt"
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
                      {/* Text input */}
                      <div className="bg-card border border-card-border rounded-2xl p-6">
                        <div className="flex items-center gap-2 mb-3">
                          <MessageSquare className="w-4 h-4 text-violet-400" />
                          <label
                            htmlFor="animation-text"
                            className="text-sm font-semibold text-foreground"
                          >
                            Que dira le portrait ?
                          </label>
                        </div>
                        <textarea
                          id="animation-text"
                          value={text}
                          onChange={(e) => setText(e.target.value)}
                          rows={3}
                          maxLength={200}
                          className="w-full bg-surface border border-card-border rounded-xl p-4 text-foreground placeholder:text-muted text-sm resize-none focus:outline-none focus:border-violet-500/50 transition-colors"
                          placeholder="Entrez le texte que le portrait animé dira..."
                        />
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-xs text-muted">
                            {text.length}/200 caractères
                          </span>
                          <span className="text-xs text-muted flex items-center gap-1">
                            <Clock className="w-3 h-3" />~30 secondes
                          </span>
                        </div>
                      </div>

                      {/* Info */}
                      <div className="bg-violet-500/5 border border-violet-500/10 rounded-xl p-4">
                        <p className="text-sm text-muted flex items-start gap-2">
                          <Sparkles className="w-4 h-4 text-violet-400 flex-shrink-0 mt-0.5" />
                          L&apos;animation utilise D-ID pour créer un portrait
                          vivant avec des expressions faciales naturelles.
                          Résultat en vidéo MP4.
                        </p>
                      </div>

                      {/* Action */}
                      <button
                        onClick={handleAnimate}
                        className="w-full inline-flex items-center justify-center gap-2 px-6 py-4 rounded-full bg-gradient-to-r from-violet-500 to-violet-600 text-white font-semibold text-base hover:brightness-110 transition-all hover:shadow-xl hover:shadow-violet-500/25 active:scale-[0.97]"
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
