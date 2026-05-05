"use client";

import { useState } from "react";
import { createCheckout } from "@/lib/api";
import { Loader2 } from "lucide-react";

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

  const handleClick = async () => {
    try {
      setLoading(true);
      setError(null);

      // Prompt for email
      const email = window.prompt(
        "Entrez votre adresse email pour continuer :"
      );
      if (!email || !email.includes("@")) {
        setError("Veuillez entrer une adresse email valide.");
        setLoading(false);
        return;
      }

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

  return (
    <div className="w-full">
      <button
        onClick={handleClick}
        disabled={loading}
        className={`w-full py-3.5 rounded-full text-sm transition-all active:scale-[0.97] inline-flex items-center justify-center gap-2 ${className}`}
      >
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : icon ? (
          icon
        ) : null}
        {loading ? "Redirection..." : label}
      </button>
      {error && (
        <p className="text-red-400 text-xs mt-2 text-center">{error}</p>
      )}
    </div>
  );
}
