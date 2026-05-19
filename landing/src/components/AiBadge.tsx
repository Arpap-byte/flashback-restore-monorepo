"use client";

import { Sparkles } from "lucide-react";

interface AiBadgeProps {
  type: "restauration" | "animation" | "colorisation";
  size?: "sm" | "md";
}

const labels: Record<string, { text: string; icon: React.ReactNode }> = {
  restauration: { text: "Restauré par IA", icon: <Sparkles className="w-3 h-3" /> },
  animation: { text: "Animé par IA", icon: <Sparkles className="w-3 h-3" /> },
  colorisation: { text: "Colorisé par IA", icon: <Sparkles className="w-3 h-3" /> },
};

export default function AiBadge({ type, size = "sm" }: AiBadgeProps) {
  const { text, icon } = labels[type] || labels.restauration;
  const sizeClasses = size === "sm" ? "text-[10px] px-2 py-0.5 gap-1" : "text-xs px-2.5 py-1 gap-1.5";

  return (
    <span
      className={`inline-flex items-center rounded-full bg-accent/10 border border-accent/20 text-accent/80 font-medium ${sizeClasses}`}
      title="Cette image a été générée ou modifiée par une intelligence artificielle"
    >
      {icon}
      {text}
    </span>
  );
}
