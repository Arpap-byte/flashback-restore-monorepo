"use client";

import { useState, useEffect } from "react";
import { createCheckout } from "@/lib/api";
import { Loader2, Mail, AlertTriangle, X, LogIn, FileText, Shield } from "lucide-react";
import { useUser, SignInButton } from "@clerk/nextjs";
import Link from "next/link";

interface StripeCheckoutButtonProps {
  plan: string;
  label: string;
  className?: string;
  icon?: React.ReactNode;
}

export default function StripeCheckoutButton({
  plan,
  label,
  className = "",
  icon,
}: StripeCheckoutButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showEmailInput, setShowEmailInput] = useState(false);
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);

  // Étape de consentement légal (CGV + renonciation rétractation)
  const [showLegalConsent, setShowLegalConsent] = useState(false);
  const [cguAccepted, setCguAccepted] = useState(false);
  const [waiverAccepted, setWaiverAccepted] = useState(false);
  const [legalError, setLegalError] = useState<string | null>(null);

  const { user, isSignedIn } = useUser();
  const clerkEmail = user?.emailAddresses?.[0]?.emailAddress;

  // Si l'utilisateur est authentifié, on lance le checkout directement
  const goToCheckout = async (userEmail: string) => {
    try {
      setLoading(true);
      setError(null);
      setEmailError(null);
      setLegalError(null);

      const result = await createCheckout(plan, userEmail);
      if (result.checkout_url) {
        window.location.href = result.checkout_url;
      } else {
        setError("URL de checkout non reçue. Veuillez réessayer.");
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Une erreur est survenue."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleInitialClick = () => {
    // Si l'utilisateur est connecté, on montre d'abord le consentement légal
    if (isSignedIn && clerkEmail) {
      setShowLegalConsent(true);
      return;
    }
    // Sinon on demande l'email
    setShowEmailInput(true);
  };

  const handleLegalConsentConfirm = () => {
    setLegalError(null);
    if (!cguAccepted) {
      setLegalError("Vous devez accepter les Conditions Générales de Vente.");
      return;
    }
    if (!waiverAccepted) {
      setLegalError("Vous devez reconnaître la renonciation au droit de rétractation.");
      return;
    }
    setShowLegalConsent(false);
    goToCheckout(clerkEmail!);
  };

  const validateEmail = (value: string): boolean => {
    if (!value.trim()) {
      setEmailError("Veuillez saisir votre adresse email.");
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      setEmailError("Veuillez entrer une adresse email valide.");
      return false;
    }
    setEmailError(null);
    return true;
  };

  const handleEmailCheckout = async () => {
    if (!validateEmail(email)) return;
    // Pour les non-connectés, on passe directement à Stripe (ils accepteront les CGV à l'inscription)
    await goToCheckout(email);
  };

  const handleCancel = () => {
    setShowEmailInput(false);
    setEmail("");
    setEmailError(null);
    setError(null);
  };

  const handleLegalCancel = () => {
    setShowLegalConsent(false);
    setCguAccepted(false);
    setWaiverAccepted(false);
    setLegalError(null);
  };

  return (
    <div className="w-full">
      {!showEmailInput && !showLegalConsent ? (
        <button
          onClick={handleInitialClick}
          disabled={loading}
          className={`w-full py-3.5 rounded-full text-sm transition-all active:scale-[0.97] inline-flex items-center justify-center gap-2 ${className}`}
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Redirection vers Stripe...
            </>
          ) : (
            <>
              {icon && icon}
              {isSignedIn ? label : "S'abonner"}
            </>
          )}
        </button>
      ) : showLegalConsent ? (
        /* --- Étape consentement légal obligatoire (utilisateurs connectés) --- */
        <div className="space-y-4 p-1">
          <p className="text-sm font-semibold text-foreground">
            Avant de continuer, veuillez accepter les conditions suivantes :
          </p>

          {/* Checkbox CGV */}
          <label className="flex items-start gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={cguAccepted}
              onChange={(e) => {
                setCguAccepted(e.target.checked);
                if (legalError) setLegalError(null);
              }}
              className="mt-1 w-4 h-4 rounded border-card-border bg-surface text-accent focus:ring-accent focus:ring-offset-0 cursor-pointer"
            />
            <span className="text-sm text-muted group-hover:text-foreground transition-colors leading-relaxed">
              J&apos;accepte les{" "}
              <Link
                href="/conditions-utilisation"
                target="_blank"
                className="text-accent hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                Conditions Générales de Vente
              </Link>{" "}
              (CGV) de Flashback Restore.{" "}
              <span className="text-red-400">*</span>
            </span>
          </label>

          {/* Checkbox renonciation rétractation */}
          <label className="flex items-start gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={waiverAccepted}
              onChange={(e) => {
                setWaiverAccepted(e.target.checked);
                if (legalError) setLegalError(null);
              }}
              className="mt-1 w-4 h-4 rounded border-card-border bg-surface text-accent focus:ring-accent focus:ring-offset-0 cursor-pointer"
            />
            <span className="text-sm text-muted group-hover:text-foreground transition-colors leading-relaxed">
              Je reconnais être informé(e) que, conformément à
              l&apos;article L.221-28 du Code de la consommation, je renonce
              expressément à mon droit de rétractation de 14 jours pour la
              fourniture immédiate de contenu numérique (photos restaurées,
              animations) après validation du paiement.{" "}
              <span className="text-red-400">*</span>
            </span>
          </label>

          {/* Erreur légal */}
          {legalError && (
            <div className="flex items-center gap-2 text-red-400 text-xs">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
              {legalError}
            </div>
          )}

          {/* Boutons */}
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleLegalConsentConfirm}
              disabled={loading}
              className={`flex-1 py-3 rounded-full text-sm transition-all active:scale-[0.97] inline-flex items-center justify-center gap-2 ${className}`}
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Shield className="w-4 h-4" />
              )}
              {loading ? "Redirection..." : "Poursuivre le paiement"}
            </button>
            <button
              onClick={handleLegalCancel}
              disabled={loading}
              className="px-4 py-3 rounded-full border border-card-border text-muted hover:text-foreground hover:border-muted transition-all text-sm flex items-center justify-center"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* API error */}
          {error && (
            <p className="text-red-400 text-xs text-center">{error}</p>
          )}
        </div>
      ) : (
        /* --- Email input (utilisateur non authentifié) --- */
        <div className="space-y-3">
          <div className="relative">
            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (emailError) validateEmail(e.target.value);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleEmailCheckout();
              }}
              placeholder="votre@email.com"
              autoFocus
              className="w-full pl-11 pr-4 py-3.5 rounded-xl bg-surface border border-card-border text-foreground placeholder:text-muted text-sm focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all"
            />
          </div>

          {emailError && (
            <div className="flex items-center gap-2 text-red-400 text-xs">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
              {emailError}
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={handleEmailCheckout}
              disabled={loading}
              className={`flex-1 py-3 rounded-full text-sm transition-all active:scale-[0.97] inline-flex items-center justify-center gap-2 ${className}`}
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                icon || <Mail className="w-4 h-4" />
              )}
              {loading ? "Redirection..." : "Payer"}
            </button>
            <button
              onClick={handleCancel}
              disabled={loading}
              className="px-4 py-3 rounded-full border border-card-border text-muted hover:text-foreground hover:border-muted transition-all text-sm flex items-center justify-center"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {error && (
            <p className="text-red-400 text-xs text-center">{error}</p>
          )}
        </div>
      )}
    </div>
  );
}
