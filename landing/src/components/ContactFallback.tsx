"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Loader2, Mail, Send, Check, X } from "lucide-react";

interface ContactFallbackProps {
  plan: string;
  onClose: () => void;
}

export default function ContactFallback({ plan, onClose }: ContactFallbackProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) {
      setError("Veuillez remplir tous les champs.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Adresse email invalide.");
      return;
    }

    setSending(true);
    setError(null);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/contact/sales`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: name.trim(), email: email.trim(), plan }),
        }
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Erreur lors de l'envoi.");
      }
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Une erreur est survenue.");
    } finally {
      setSending(false);
    }
  };

  if (sent) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-6 rounded-xl bg-green-500/5 border border-green-500/20 text-center"
      >
        <div className="mx-auto w-12 h-12 rounded-full bg-green-500/10 flex items-center justify-center mb-3">
          <Check className="w-6 h-6 text-green-400" />
        </div>
        <p className="text-sm font-semibold text-foreground mb-1">Demande envoyée !</p>
        <p className="text-xs text-muted">
          Nous vous recontacterons rapidement à l&apos;adresse{" "}
          <span className="text-foreground font-medium">{email}</span>.
        </p>
      </motion.div>
    );
  }

  return (
    <motion.form
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      onSubmit={handleSubmit}
      className="space-y-3 p-1"
    >
      <p className="text-sm text-muted mb-1">
        Notre service de paiement est momentanément indisponible. Laissez-nous
        vos coordonnées et nous vous recontacterons pour finaliser votre
        abonnement <span className="text-foreground font-medium capitalize">{plan}</span>.
      </p>

      {/* Name */}
      <div className="relative">
        <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
        <input
          type="text"
          value={name}
          onChange={(e) => { setName(e.target.value); if (error) setError(null); }}
          placeholder="Votre nom"
          autoFocus
          className="w-full pl-11 pr-4 py-3 rounded-xl bg-surface border border-card-border text-foreground placeholder:text-muted text-sm focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all"
        />
      </div>

      {/* Email */}
      <div className="relative">
        <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
        <input
          type="email"
          value={email}
          onChange={(e) => { setEmail(e.target.value); if (error) setError(null); }}
          placeholder="votre@email.com"
          className="w-full pl-11 pr-4 py-3 rounded-xl bg-surface border border-card-border text-foreground placeholder:text-muted text-sm focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all"
        />
      </div>

      {error && <p className="text-red-400 text-xs">{error}</p>}

      <div className="flex gap-2 pt-1">
        <button
          type="submit"
          disabled={sending}
          className="flex-1 py-3 rounded-full bg-accent text-white font-semibold text-sm hover:brightness-110 transition-all active:scale-[0.97] inline-flex items-center justify-center gap-2"
        >
          {sending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
          {sending ? "Envoi..." : "Envoyer"}
        </button>
        <button
          type="button"
          onClick={onClose}
          disabled={sending}
          className="px-4 py-3 rounded-full border border-card-border text-muted hover:text-foreground transition-all text-sm flex items-center justify-center"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </motion.form>
  );
}
