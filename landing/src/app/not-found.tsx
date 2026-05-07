import Link from "next/link";
import { Home, Search, Film } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      {/* Background glow */}
      <div className="absolute top-[20%] left-[10%] w-[450px] h-[450px] bg-violet-600/5 rounded-full blur-[130px] pointer-events-none" />
      <div className="absolute bottom-[20%] right-[10%] w-[400px] h-[400px] bg-accent/5 rounded-full blur-[100px] pointer-events-none" />

      <div className="relative z-10 max-w-lg w-full text-center">
        {/* Large 404 */}
        <div className="relative inline-block mb-8">
          <h1 className="text-[8rem] sm:text-[10rem] font-black leading-none text-gradient select-none">
            404
          </h1>
          {/* Decorative film strip */}
          <div className="absolute -top-4 -right-8 sm:-right-12 opacity-20">
            <Film className="w-10 h-10 sm:w-14 sm:h-14 text-accent rotate-12" />
          </div>
        </div>

        {/* Message card */}
        <div className="bg-card rounded-2xl border border-card-border p-8 sm:p-10 shadow-2xl shadow-black/10">
          <div className="mx-auto mb-4 w-14 h-14 rounded-2xl bg-accent/10 flex items-center justify-center">
            <Search className="w-7 h-7 text-accent" />
          </div>

          <h2 className="text-xl sm:text-2xl font-bold text-foreground mb-3 font-[family-name:var(--font-playfair)]">
            Page introuvable
          </h2>

          <p className="text-muted leading-relaxed mb-8">
            Le souvenir que vous cherchez semble s&apos;être égaré dans le temps.
            Cette page n&apos;existe pas ou a été déplacée.
          </p>

          <Link
            href="/"
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-base hover:brightness-110 transition-all hover:shadow-xl hover:shadow-accent/30 active:scale-[0.97]"
          >
            <Home className="w-5 h-5" />
            Retour à l&apos;accueil
          </Link>
        </div>

        {/* Decorative bottom bar */}
        <div className="mt-4 h-1 rounded-full bg-gradient-to-r from-transparent via-accent/30 to-violet-400/20" />
      </div>
    </div>
  );
}
