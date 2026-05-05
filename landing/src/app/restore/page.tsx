"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  Sparkles,
  ArrowRight,
  AlertTriangle,
  X,
  Download,
  Play,
  Check,
  RefreshCw,
  Image as ImageIcon,
  ArrowLeftRight,
  Zap,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { restorePhoto, getRestoredImageUrl, RestoreResult } from "@/lib/api";

const steps = [
  { key: "analyse", label: "Analyse de l'image" },
  { key: "parametres", label: "Paramètres de restauration" },
  { key: "restauration", label: "Restauration IA" },
  { key: "rendu", label: "Rendu final" },
];

export default function RestorePage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [restoreResult, setRestoreResult] = useState<RestoreResult | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [showAfter, setShowAfter] = useState(true);
  const [sliderPos, setSliderPos] = useState(50);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const sliderRef = useRef<HTMLDivElement>(null);

  // On mount, check for photo passed from upload page
  useEffect(() => {
    const stored = sessionStorage.getItem("flashback_photo");
    if (stored) {
      setPreview(stored);
      // Convert data URL to File for API call
      fetch(stored)
        .then((res) => res.blob())
        .then((blob) => {
          const f = new File([blob], "photo.jpg", { type: "image/jpeg" });
          setFile(f);
        })
        .catch(() => {});
    }
  }, []);

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
    setRestoreResult(null);
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

  // Animate fake progress steps
  useEffect(() => {
    if (!restoring) return;
    const intervals = [1500, 3000, 5500, 8000];
    const timers = intervals.map((delay, i) =>
      setTimeout(() => setCurrentStep(i + 1), delay)
    );
    return () => timers.forEach(clearTimeout);
  }, [restoring]);

  const handleRestore = async () => {
    if (!file) return;
    setRestoring(true);
    setCurrentStep(1);
    setError(null);
    try {
      const result = await restorePhoto(file);
      setRestoreResult(result);
      setCurrentStep(4);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erreur lors de la restauration. Veuillez réessayer."
      );
    } finally {
      setRestoring(false);
    }
  };

  const handleClear = () => {
    setFile(null);
    setPreview(null);
    setRestoreResult(null);
    setError(null);
    setCurrentStep(0);
    sessionStorage.removeItem("flashback_photo");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const restoredUrl = restoreResult
    ? getRestoredImageUrl(restoreResult.filename)
    : null;

  // Download handler
  const handleDownload = async (url: string, name: string) => {
    try {
      const res = await fetch(url);
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch {
      window.open(url, "_blank");
    }
  };

  // Slider drag
  const handleSliderMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startPos = sliderPos;

    const onMove = (ev: MouseEvent) => {
      const dx = ev.clientX - startX;
      const rect = sliderRef.current?.getBoundingClientRect();
      if (!rect) return;
      const newPos = Math.max(0, Math.min(100, startPos + (dx / rect.width) * 100));
      setSliderPos(newPos);
    };

    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  };

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 pt-24 pb-16">
        {/* Background glow */}
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute top-1/4 right-1/4 w-[600px] h-[600px] bg-violet-600/6 rounded-full blur-[120px]" />
          <div className="absolute bottom-1/4 left-1/4 w-[500px] h-[500px] bg-accent/5 rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-12"
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 border border-accent/20 text-accent text-sm font-medium mb-6">
              <Sparkles className="w-4 h-4" />
              Étape 2 — Restauration
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              Restauration
              <br />
              <span className="text-gradient">par intelligence artificielle</span>
            </h1>
            <p className="text-muted text-lg max-w-xl mx-auto">
              Notre IA corrige automatiquement les défauts de votre photo :
              rayures, taches, déchirures et couleurs délavées.
            </p>
          </motion.div>

          {/* Main content */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            {!preview ? (
              /* Upload zone (no photo yet) */
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
                    ? "border-accent bg-accent/5 scale-[1.01]"
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
                    className="w-20 h-20 rounded-2xl bg-accent/10 flex items-center justify-center"
                  >
                    <Upload className="w-10 h-10 text-accent" />
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
            ) : !restoring && !restoreResult ? (
              /* Photo loaded, ready to restore */
              <div className="grid lg:grid-cols-5 gap-8">
                <div className="lg:col-span-2">
                  <div className="relative rounded-2xl overflow-hidden border border-card-border bg-card shadow-xl">
                    <img
                      src={preview}
                      alt="Photo à restaurer"
                      className="w-full aspect-[4/3] object-contain bg-surface-alt"
                    />
                    <button
                      onClick={handleClear}
                      className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/50 backdrop-blur text-white flex items-center justify-center hover:bg-black/70 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="lg:col-span-3 flex flex-col items-center justify-center text-center p-8">
                  <Sparkles className="w-12 h-12 text-accent mb-4" />
                  <h3 className="text-xl font-semibold text-foreground mb-2">
                    Prêt pour la restauration
                  </h3>
                  <p className="text-muted mb-8">
                    Notre IA va analyser et réparer automatiquement les défauts
                    de votre photo. Cliquez sur le bouton ci-dessous pour lancer
                    la magie.
                  </p>
                  <button
                    onClick={handleRestore}
                    className="group inline-flex items-center gap-2 px-8 py-4 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-base hover:brightness-110 transition-all hover:shadow-xl hover:shadow-accent/30 active:scale-[0.97]"
                  >
                    <Sparkles className="w-5 h-5" />
                    Restaurer la photo
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              </div>
            ) : restoring ? (
              /* Restoring progress */
              <div className="max-w-lg mx-auto text-center py-8">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "linear",
                  }}
                  className="w-20 h-20 rounded-full border-2 border-accent/30 border-t-accent mx-auto mb-8"
                />
                <h3 className="text-xl font-semibold text-foreground mb-6">
                  Restauration en cours...
                </h3>
                <div className="space-y-3 max-w-xs mx-auto">
                  {steps.map((step, i) => (
                    <div
                      key={step.key}
                      className="flex items-center gap-3"
                    >
                      <div
                        className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold transition-all duration-300 ${
                          i < currentStep
                            ? "bg-emerald-500 text-white"
                            : i === currentStep
                            ? "bg-accent text-white animate-pulse"
                            : "bg-surface text-muted"
                        }`}
                      >
                        {i < currentStep ? (
                          <Check className="w-3.5 h-3.5" />
                        ) : (
                          i + 1
                        )}
                      </div>
                      <span
                        className={`text-sm transition-colors ${
                          i <= currentStep ? "text-foreground" : "text-muted"
                        }`}
                      >
                        {step.label}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="mt-8 w-full max-w-xs mx-auto h-1.5 rounded-full bg-surface overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-accent to-violet-500"
                    initial={{ width: "0%" }}
                    animate={{
                      width: `${(currentStep / steps.length) * 100}%`,
                    }}
                    transition={{ duration: 1 }}
                  />
                </div>
              </div>
            ) : restoreResult ? (
              /* Result: Before/After */
              <div className="space-y-8">
                {/* View toggle */}
                <div className="flex items-center justify-center gap-3">
                  <button
                    onClick={() => setShowAfter(false)}
                    className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                      !showAfter
                        ? "bg-accent text-white dark:text-gray-950"
                        : "bg-surface text-muted hover:text-foreground"
                    }`}
                  >
                    Avant
                  </button>
                  <button
                    onClick={() => setShowAfter(true)}
                    className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                      showAfter
                        ? "bg-accent text-white dark:text-gray-950"
                        : "bg-surface text-muted hover:text-foreground"
                    }`}
                  >
                    Après
                  </button>
                  <button
                    onClick={() => setShowAfter(!showAfter)}
                    className="px-4 py-2 rounded-full text-sm font-medium bg-surface text-muted hover:text-foreground transition-all flex items-center gap-1.5"
                  >
                    <ArrowLeftRight className="w-3.5 h-3.5" />
                    Comparer
                  </button>
                </div>

                {/* Slider comparison */}
                <div
                  ref={sliderRef}
                  className="relative rounded-2xl overflow-hidden border border-card-border bg-card shadow-2xl cursor-col-resize select-none"
                  onMouseDown={handleSliderMouseDown}
                >
                  <div className="relative w-full max-h-[500px] aspect-[4/3] overflow-hidden">
                    {/* After (full) */}
                    <img
                      src={restoredUrl!}
                      alt="Photo restaurée"
                      className="absolute inset-0 w-full h-full object-contain bg-surface-alt"
                    />
                    {/* Before (clipped) */}
                    <div
                      className="absolute inset-0 overflow-hidden"
                      style={{ width: `${sliderPos}%` }}
                    >
                      <img
                        src={preview!}
                        alt="Photo originale"
                        className="absolute inset-0 w-full h-full object-contain bg-surface-alt"
                        style={{
                          width: `${(100 / sliderPos) * 100}%`,
                        }}
                      />
                    </div>
                    {/* Slider handle */}
                    <div
                      className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg shadow-black/30"
                      style={{ left: `${sliderPos}%` }}
                    >
                      <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-10 h-10 rounded-full bg-white shadow-xl flex items-center justify-center">
                        <ArrowLeftRight className="w-5 h-5 text-gray-800" />
                      </div>
                    </div>
                    {/* Labels */}
                    <div className="absolute top-3 left-3 px-3 py-1 rounded-full bg-black/60 backdrop-blur text-white text-xs font-medium">
                      Avant
                    </div>
                    <div className="absolute top-3 right-3 px-3 py-1 rounded-full bg-accent/80 backdrop-blur text-white text-xs font-medium flex items-center gap-1">
                      <Sparkles className="w-3 h-3" />
                      Après
                    </div>
                  </div>
                </div>

                {/* Mobile fallback: toggle view */}
                <div className="lg:hidden">
                  <div className="relative rounded-2xl overflow-hidden border border-card-border bg-card shadow-xl">
                    <img
                      src={!showAfter ? preview! : restoredUrl!}
                      alt={!showAfter ? "Avant" : "Après"}
                      className="w-full aspect-[4/3] object-contain bg-surface-alt"
                    />
                    <div className="absolute top-3 left-3 px-3 py-1 rounded-full bg-black/60 backdrop-blur text-white text-xs font-medium">
                      {!showAfter ? "Avant" : "Après ✨"}
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex flex-col sm:flex-row items-center gap-3">
                  <button
                    onClick={() =>
                      restoredUrl &&
                      handleDownload(restoredUrl, "flashback-restored.jpg")
                    }
                    className="flex-1 inline-flex items-center justify-center gap-2 px-6 py-4 rounded-full bg-accent text-white dark:text-gray-950 font-semibold hover:brightness-110 transition-all hover:shadow-xl hover:shadow-accent/30 active:scale-[0.97]"
                  >
                    <Download className="w-5 h-5" />
                    Télécharger la photo restaurée
                  </button>
                  <button
                    onClick={() => {
                      if (restoredUrl) {
                        sessionStorage.setItem("flashback_photo", restoredUrl);
                      }
                      window.location.href = "/animate";
                    }}
                    className="flex-1 inline-flex items-center justify-center gap-2 px-6 py-4 rounded-full border-2 border-violet-500/30 text-foreground hover:bg-violet-500/10 hover:border-violet-400 font-semibold transition-all active:scale-[0.97]"
                  >
                    <Play className="w-5 h-5 text-violet-400" />
                    Animer cette photo
                  </button>
                  <button
                    onClick={handleClear}
                    className="flex items-center justify-center gap-2 px-6 py-4 rounded-full border border-card-border text-muted hover:text-foreground hover:border-muted transition-all"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Nouvelle photo
                  </button>
                </div>
              </div>
            ) : null}

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
