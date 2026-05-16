"use client";

import { Share2, Link2 } from "lucide-react";

export function ShareButtons({
  url,
  title,
}: {
  url: string;
  title: string;
}) {
  return (
    <div className="flex items-center gap-3 mb-10 pb-8 border-b border-card-border">
      <span className="text-sm text-muted flex items-center gap-1.5">
        <Share2 className="w-4 h-4" />
        Partager :
      </span>
      <a
        href={`https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`}
        target="_blank"
        rel="noopener noreferrer"
        className="w-9 h-9 rounded-lg bg-card border border-card-border flex items-center justify-center text-muted hover:text-accent hover:border-accent/30 hover:bg-accent/5 transition-all"
        aria-label="Partager sur Twitter"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
        </svg>
      </a>
      <a
        href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`}
        target="_blank"
        rel="noopener noreferrer"
        className="w-9 h-9 rounded-lg bg-card border border-card-border flex items-center justify-center text-muted hover:text-accent hover:border-accent/30 hover:bg-accent/5 transition-all"
        aria-label="Partager sur Facebook"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
        </svg>
      </a>
      <button
        onClick={() => {
          navigator.clipboard.writeText(url);
        }}
        className="w-9 h-9 rounded-lg bg-card border border-card-border flex items-center justify-center text-muted hover:text-accent hover:border-accent/30 hover:bg-accent/5 transition-all"
        aria-label="Copier le lien"
        title="Copier le lien"
      >
        <Link2 className="w-4 h-4" />
      </button>
    </div>
  );
}
