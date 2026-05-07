import { Loader2, Sparkles } from "lucide-react";

export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      {/* Background glow accents */}
      <div className="absolute top-[30%] left-[15%] w-[400px] h-[400px] bg-violet-600/6 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[25%] right-[10%] w-[350px] h-[350px] bg-accent/6 rounded-full blur-[100px] pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center gap-8">
        {/* Spinner with layered rings */}
        <div className="relative">
          {/* Outer ring */}
          <div className="absolute inset-[-12px] rounded-full border-2 border-accent/10 animate-[spin_3s_linear_infinite]" />
          {/* Middle ring */}
          <div className="absolute inset-[-6px] rounded-full border-2 border-violet-400/15 animate-[spin_2s_linear_infinite_reverse]" />
          {/* Inner spinner */}
          <div className="w-16 h-16 rounded-full border-2 border-accent/30 border-t-accent animate-[spin_0.8s_linear_infinite]" />
          {/* Center sparkle */}
          <div className="absolute inset-0 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-accent animate-pulse" />
          </div>
        </div>

        {/* Skeleton text bars */}
        <div className="flex flex-col items-center gap-3 w-64">
          <div className="h-3 w-full rounded-full bg-surface-alt animate-shimmer overflow-hidden relative">
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-accent/10 to-transparent animate-[shimmer_2s_ease-in-out_infinite]" />
          </div>
          <div className="h-3 w-3/4 rounded-full bg-surface-alt animate-shimmer overflow-hidden relative">
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-violet-400/8 to-transparent animate-[shimmer_2s_ease-in-out_infinite_0.3s]" />
          </div>
          <div className="h-3 w-1/2 rounded-full bg-surface-alt animate-shimmer overflow-hidden relative">
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-accent/8 to-transparent animate-[shimmer_2s_ease-in-out_infinite_0.6s]" />
          </div>
        </div>

        <p className="text-muted text-sm font-medium flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin text-accent" />
          Chargement en cours…
        </p>
      </div>
    </div>
  );
}
