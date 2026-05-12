"use client";

import { useState } from "react";
import { createCheckout } from "@/lib/api";
import { Loader2, Mail, AlertTriangle, X } from "lucide-react";

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

  const handleCheckout = async () => {
    if (!validateEmail(email)) return;

    try {
      setLoading(true);
      setError(null);
      setEmailError(null);

      const result = await createCheckout(plan, email);
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
    setShowEmailInput(true);
  };

  const handleCancel = () => {
    setShowEmailInput(false);
    setEmail("");
    setEmailError(null);
    setError(null);
  };

  return (
    <div className="w-full">
      {!showEmailInput ? (
        <button
          onClick={handleInitialClick}
          className={`w-full py-3.5 rounded-full text-sm transition-all active:scale-[0.97] inline-flex items-center justify-center gap-2 ${className}`}
        >
          {icon && icon}
          {label}
        </button>
      ) : (
        <div className="space-y-3">
          {/* Email input */}
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
                if (e.key === "Enter") handleCheckout();
              }}
              placeholder="votre@email.com"
              autoFocus
              className="w-full pl-11 pr-4 py-3.5 rounded-xl bg-surface border border-card-border text-foreground placeholder:text-muted text-sm focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all"
            />
          </div>

          {/* Validation error */}
          {emailError && (
            <div className="flex items-center gap-2 text-red-400 text-xs">
              <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
              {emailError}
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-2">
            <button
              onClick={handleCheckout}
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

          {/* API error */}
          {error && (
            <p className="text-red-400 text-xs text-center">{error}</p>
          )}
        </div>
      )}
    </div>
  );
}
