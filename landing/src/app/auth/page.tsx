"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function AuthRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const mode = searchParams.get("mode"); // register or login
    const callbackUrl = searchParams.get("callbackUrl") || "/restore";
    
    if (mode === "register") {
      router.replace(`/sign-up?redirect_url=${encodeURIComponent(callbackUrl)}`);
    } else {
      router.replace(`/sign-in?redirect_url=${encodeURIComponent(callbackUrl)}`);
    }
  }, [router, searchParams]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 rounded-full border-3 border-accent/30 border-t-accent animate-spin mx-auto mb-4" />
        <p className="text-muted text-sm">Redirection vers l&apos;authentification...</p>
      </div>
    </div>
  );
}
