"use client";

import { useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  Image as ImageIcon,
  Sparkles,
  ArrowRight,
  AlertTriangle,
  X,
  FileImage,
  Camera,
  Shield,
  Zap,
  RefreshCw,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { analyzePhoto, AnalysisResult } from "@/lib/api";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    setAnalysis(null);
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

  const handleAnalyze = async () => {
    if (!file) return;
    setAnalyzing(true);
    setError(null);
    try {
      const result = await analyzePhoto(file);
      setAnalysis(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erreur lors de l'analyse. Veuillez réessayer."
      );
    } finally {
      setAnalyzing(false);
    }
  };

  const handleClear = () => {
    setFile(null);
    setPreview(null);
    setAnalysis(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const conditionLabel = (c: string) => {
    switch (c) {
      case "excellent":
        return "Excellent";
      case "bon":
        return "Bon";
      case "moyen":
        return "Moyen";
      case "mauvais":
        return "Mauvais";
      case "tres_mauvais":
        return "Très mauvais";
      default:
        return c;
    }
  };

  const conditionColor = (c: string) => {
    switch (c) {
      case "excellent":
        return "text-emerald-400";
      case "bon":
        return "text-emerald-500";
      case "moyen":
        return "text-amber-400";
      case "mauvais":
        return "text-orange-400";
      case "tres_mauvais":
        return "text-red-400";
      default:
        return "text-muted";
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Navbar />
      <main className="flex-1 pt-24 pb-16">
        {/* Background glow */}
        <div className="fixed inset-0 pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-violet-600/6 rounded-full blur-[120px]" />
          <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-accent/5 rounded-full blur-[100px]" />
        </div>

        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-12"
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 border border-accent/20 text-accent text-sm font-medium mb-6">
              <Camera className="w-4 h-4" />
              Étape 1 — Analyse
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4 font-[family-name:var(--font-playfair)]">
              Téléchargez votre
              <br />
              <span className="text-gradient">photo ancienne</span>
            </h1>
            <p className="text-muted text-lg max-w-xl mx-auto">
              Notre IA analyse votre photo pour identifier les défauts à
              restaurer. Formats acceptés : JPG, PNG, WebP — 20 Mo max.
            </p>
          </motion.div>

          {/* Upload zone */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            {!preview ? (
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
                  <div className="flex items-center gap-6 text-xs text-muted mt-2">
                    <span className="flex items-center gap-1">
                      <FileImage className="w-3.5 h-3.5" />
                      JPG, PNG, WebP
                    </span>
                    <span className="flex items-center gap-1">
                      <Shield className="w-3.5 h-3.5" />
                      20 Mo max
                    </span>
                    <span className="flex items-center gap-1">
                      <Zap className="w-3.5 h-3.5" />
                      Analyse IA instantanée
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="grid lg:grid-cols-5 gap-8"
              >
                {/* Preview */}
                <div className="lg:col-span-2">
                  <div className="relative rounded-2xl overflow-hidden border border-card-border bg-card shadow-xl">
                    <img
                      src={preview}
                      alt="Aperçu de la photo"
                      className="w-full aspect-[4/3] object-contain bg-surface-alt"
                    />
                    <button
                      onClick={handleClear}
                      className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/50 backdrop-blur text-white flex items-center justify-center hover:bg-black/70 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                    <div className="px-4 py-2.5 border-t border-card-border flex items-center gap-2 text-xs text-muted">
                      <FileImage className="w-3.5 h-3.5" />
                      {file?.name} (
                      {file && (file.size / (1024 * 1024)).toFixed(1)} Mo)
                    </div>
                  </div>
                </div>

                {/* Actions & Results */}
                <div className="lg:col-span-3 flex flex-col gap-6">
                  {!analyzing && !analysis && (
                    <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
                      <ImageIcon className="w-12 h-12 text-muted mb-4 opacity-50" />
                      <p className="text-muted mb-6">
                        Photo chargée. Lancez l&apos;analyse IA pour connaître
                        les défauts détectés.
                      </p>
                      <button
                        onClick={handleAnalyze}
                        className="group inline-flex items-center gap-2 px-8 py-4 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-base hover:brightness-110 transition-all hover:shadow-xl hover:shadow-accent/30 active:scale-[0.97]"
                      >
                        <Sparkles className="w-5 h-5" />
                        Analyser la photo
                        <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                      </button>
                    </div>
                  )}

                  {analyzing && (
                    <div className="flex-1 flex flex-col items-center justify-center p-8">
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{
                          duration: 2,
                          repeat: Infinity,
                          ease: "linear",
                        }}
                        className="w-16 h-16 rounded-full border-2 border-accent/30 border-t-accent mb-6"
                      />
                      <p className="text-foreground font-semibold text-lg mb-2">
                        Analyse en cours...
                      </p>
                      <p className="text-muted text-sm">
                        L&apos;IA examine votre photo pour détecter les défauts
                      </p>
                      <div className="mt-6 w-full max-w-xs h-1.5 rounded-full bg-surface overflow-hidden">
                        <motion.div
                          className="h-full rounded-full bg-gradient-to-r from-accent to-violet-500"
                          initial={{ width: "0%" }}
                          animate={{ width: "100%" }}
                          transition={{ duration: 3, repeat: Infinity }}
                        />
                      </div>
                    </div>
                  )}

                  {analysis && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="space-y-5"
                    >
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-5 h-5 text-accent" />
                        <h3 className="text-lg font-semibold text-foreground">
                          Résultats de l&apos;analyse
                        </h3>
                      </div>

                      {/* Defects grid */}
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                        {[
                          {
                            label: "Rayures",
                            value: analysis.scratches,
                            emoji: "〰️",
                          },
                          {
                            label: "Décoloration",
                            value: analysis.fading,
                            emoji: "🎨",
                          },
                          {
                            label: "Taches",
                            value: analysis.stains,
                            emoji: "💧",
                          },
                          {
                            label: "Déchirures",
                            value: analysis.tears,
                            emoji: "✂️",
                          },
                          {
                            label: "Bruit",
                            value: analysis.noise,
                            emoji: "📡",
                          },
                        ].map((defect) => (
                          <div
                            key={defect.label}
                            className="bg-card border border-card-border rounded-xl p-3"
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs text-muted">
                                {defect.emoji} {defect.label}
                              </span>
                              <span className="text-xs font-bold text-foreground">
                                {defect.value}/10
                              </span>
                            </div>
                            <div className="h-1.5 rounded-full bg-surface overflow-hidden">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{
                                  width: `${defect.value * 10}%`,
                                }}
                                transition={{ duration: 0.8 }}
                                className={`h-full rounded-full ${
                                  defect.value > 7
                                    ? "bg-red-500"
                                    : defect.value > 4
                                    ? "bg-amber-500"
                                    : "bg-emerald-500"
                                }`}
                              />
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Condition & Age */}
                      <div className="grid sm:grid-cols-2 gap-3">
                        <div className="bg-card border border-card-border rounded-xl p-4">
                          <span className="text-xs text-muted">
                            État général
                          </span>
                          <p
                            className={`text-lg font-bold mt-1 ${conditionColor(analysis.condition)}`}
                          >
                            {conditionLabel(analysis.condition)}
                          </p>
                        </div>
                        <div className="bg-card border border-card-border rounded-xl p-4">
                          <span className="text-xs text-muted">Âge estimé</span>
                          <p className="text-lg font-bold text-foreground mt-1">
                            {analysis.estimated_age}
                          </p>
                        </div>
                      </div>

                      {/* Recommendations */}
                      {analysis.recommendations?.length > 0 && (
                        <div className="bg-card border border-card-border rounded-xl p-4">
                          <span className="text-xs text-muted mb-2 block">
                            Recommandations
                          </span>
                          <ul className="space-y-1.5">
                            {analysis.recommendations.map((rec, i) => (
                              <li
                                key={i}
                                className="text-sm text-foreground flex items-start gap-2"
                              >
                                <span className="text-accent mt-0.5">•</span>
                                {rec}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Action buttons */}
                      <div className="flex flex-col sm:flex-row gap-3 pt-2">
                        <button
                          onClick={() => {
                            // Store preview in sessionStorage for the restore page
                            if (preview) {
                              sessionStorage.setItem(
                                "flashback_photo",
                                preview
                              );
                            }
                            window.location.href = "/restore";
                          }}
                          className="group flex-1 inline-flex items-center justify-center gap-2 px-6 py-4 rounded-full bg-accent text-white dark:text-gray-950 font-semibold hover:brightness-110 transition-all hover:shadow-xl hover:shadow-accent/30 active:scale-[0.97]"
                        >
                          Restaurer cette photo
                          <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        </button>
                        <button
                          onClick={handleClear}
                          className="flex items-center justify-center gap-2 px-6 py-4 rounded-full border border-card-border text-muted hover:text-foreground hover:border-muted transition-all"
                        >
                          <RefreshCw className="w-4 h-4" />
                          Nouvelle photo
                        </button>
                      </div>
                    </motion.div>
                  )}
                </div>
              </motion.div>
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
