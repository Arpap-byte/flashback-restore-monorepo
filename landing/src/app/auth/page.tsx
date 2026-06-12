"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function AuthRedirectInner() {
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
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-muted animate-pulse">Redirection en cours...</p>
    </div>
  );
}

export default function AuthRedirect() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="animate-pulse text-muted">Chargement...</div></div>}>
      <AuthRedirectInner />
    </Suspense>
  );
}
