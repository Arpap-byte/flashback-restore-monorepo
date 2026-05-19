"use client";

import { useState, useEffect } from "react";
import { Shield, AlertTriangle } from "lucide-react";
import Link from "next/link";

interface RgpdConsentProps {
  isOpen: boolean;
  onAccept: () => void;
  onDecline: () => void;
}

export function RgpdConsentModal({ isOpen, onAccept, onDecline }: RgpdConsentProps) {
  const [processingAccepted, setProcessingAccepted] = useState(false);
  const [aiAccepted, setAiAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleConfirm = () => {
    setError(null);
    if (!processingAccepted) {
      setError("Vous devez accepter le traitement de vos données.");
      return;
    }
    if (!aiAccepted) {
      setError("Vous devez accepter l'utilisation de l'intelligence artificielle.");
      return;
    }
    onAccept();
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Modal */}
      <div className="relative z-10 bg-card border border-card-border rounded-2xl p-6 sm:p-8 max-w-lg w-full shadow-2xl animate-in fade-in zoom-in-95">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center">
            <Shield className="w-5 h-5 text-accent" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">
              Protection de vos données
            </h3>
            <p className="text-sm text-muted">Consentement RGPD</p>
          </div>
        </div>

        <div className="space-y-4 mb-6">
          <div className="p-3 rounded-xl bg-accent/5 border border-accent/10 text-sm text-muted">
            <AlertTriangle className="w-4 h-4 text-accent inline mr-2" />
            Pour utiliser Flashback Restore, notre intelligence artificielle
            doit analyser vos photos. Cela implique un traitement temporaire
            de données potentiellement biométriques (traits du visage).
          </div>

          {/* Checkbox 1 — Traitement */}
          <label className="flex items-start gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={processingAccepted}
              onChange={(e) => {
                setProcessingAccepted(e.target.checked);
                if (error) setError(null);
              }}
              className="mt-0.5 w-4 h-4 rounded border-card-border bg-surface text-accent focus:ring-accent cursor-pointer"
            />
            <span className="text-sm text-muted group-hover:text-foreground transition-colors leading-relaxed">
              J&apos;accepte que mes photos soient temporairement transmises
              et traitées par l&apos;intelligence artificielle de Flashback
              Restore aux fins de restauration, colorisation et/ou animation.{" "}
              <span className="text-red-400">*</span>
            </span>
          </label>

          {/* Checkbox 2 — IA */}
          <label className="flex items-start gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={aiAccepted}
              onChange={(e) => {
                setAiAccepted(e.target.checked);
                if (error) setError(null);
              }}
              className="mt-0.5 w-4 h-4 rounded border-card-border bg-surface text-accent focus:ring-accent cursor-pointer"
            />
            <span className="text-sm text-muted group-hover:text-foreground transition-colors leading-relaxed">
              Je reconnais que mes photos seront traitées par une technologie
              d&apos;intelligence artificielle. Je comprends qu&apos;aucun
              humain ne visualise mes images et que les données sont
              automatiquement supprimées après traitement, conformément à la{" "}
              <Link
                href="/privacy"
                target="_blank"
                className="text-accent hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                Politique de Confidentialité
              </Link>
              .{" "}
              <span className="text-red-400">*</span>
            </span>
          </label>

          {error && (
            <p className="text-xs text-red-400 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              {error}
            </p>
          )}

          <p className="text-xs text-muted/60">
            Vous pourrez retirer votre consentement à tout moment en nous
            contactant. Ce consentement est requis pour utiliser le service.
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleConfirm}
            className="flex-1 py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-sm hover:brightness-110 transition-all active:scale-[0.97]"
          >
            J&apos;accepte et je continue
          </button>
          <button
            onClick={onDecline}
            className="flex-1 py-3 rounded-full border border-card-border text-muted hover:text-foreground transition-all text-sm"
          >
            Refuser
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook de consentement RGPD.
 * Vérifie localStorage pour savoir si l'utilisateur a déjà donné son consentement.
 */
export function useRgpdConsent() {
  const RGPD_KEY = "flashback_rgpd_consent_v1";

  const [showConsent, setShowConsent] = useState(false);
  const [consentGiven, setConsentGiven] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(RGPD_KEY);
    if (stored === "true") {
      setConsentGiven(true);
    }
  }, []);

  const requireConsent = (): Promise<boolean> => {
    return new Promise((resolve) => {
      if (consentGiven) {
        resolve(true);
        return;
      }
      // Show modal - the component will handle the result
      setShowConsent(true);

      // Store the resolver
      (window as any).__flashback_rgpd_resolve = (accepted: boolean) => {
        if (accepted) {
          localStorage.setItem(RGPD_KEY, "true");
          setConsentGiven(true);
        }
        setShowConsent(false);
        resolve(accepted);
      };
    });
  };

  const handleAccept = () => {
    (window as any).__flashback_rgpd_resolve?.(true);
  };

  const handleDecline = () => {
    (window as any).__flashback_rgpd_resolve?.(false);
  };

  return {
    showConsent,
    consentGiven,
    requireConsent,
    handleAccept,
    handleDecline,
    RgpdModal: (
      <RgpdConsentModal
        isOpen={showConsent}
        onAccept={handleAccept}
        onDecline={handleDecline}
      />
    ),
  };
}
