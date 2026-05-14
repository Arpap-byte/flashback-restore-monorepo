"use client";

import { useUser, useClerk } from "@clerk/nextjs";
import React, { createContext, useContext, useMemo, useCallback, useEffect } from "react";

export interface User {
  id: string;
  email: string;
  name?: string;
  image?: string;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState>({
  user: null,
  loading: true,
  logout: async () => {},
});

function AuthInner({ children }: { children: React.ReactNode }) {
  const { user: clerkUser, isLoaded } = useUser();
  const { signOut } = useClerk();

  const user = useMemo(() => {
    if (!clerkUser || !isLoaded) return null;
    const primaryEmail = clerkUser.emailAddresses?.[0]?.emailAddress;
    return {
      id: clerkUser.id,
      email: primaryEmail || clerkUser.id,
      name: `${clerkUser.firstName || ""} ${clerkUser.lastName || ""}`.trim() || primaryEmail || undefined,
      image: clerkUser.imageUrl,
    };
  }, [clerkUser, isLoaded]);

  const logout = useCallback(async () => {
    // Nettoyer les donnees de session partagees avant la deconnexion
    sessionStorage.removeItem("flashback_photo");
    sessionStorage.removeItem("flashback_user_id");
    await signOut();
  }, [signOut]);

  // Nettoyer sessionStorage quand l'utilisateur change (empeche les fuites cross-compte)
  useEffect(() => {
    if (user?.id) {
      const storedId = sessionStorage.getItem("flashback_user_id");
      if (storedId && storedId !== user.id) {
        sessionStorage.removeItem("flashback_photo");
      }
      sessionStorage.setItem("flashback_user_id", user.id);
    } else if (isLoaded) {
      // Deconnecte
      sessionStorage.removeItem("flashback_photo");
      sessionStorage.removeItem("flashback_user_id");
    }
  }, [user?.id, isLoaded]);

  return (
    <AuthContext.Provider value={{ user, loading: !isLoaded, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return <AuthInner>{children}</AuthInner>;
}

export function useAuth() {
  return useContext(AuthContext);
}
