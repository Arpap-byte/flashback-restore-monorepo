"use client";

import { SessionProvider, useSession, signOut as nextAuthSignOut } from "next-auth/react";
import React, { createContext, useContext } from "react";

export interface User {
  id: string;
  email: string;
  essais_restants: number;
  est_abonne: boolean;
  credits: number;
}

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null,
  token: null,
  loading: true,
  logout: () => {},
});

function AuthInner({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();

  const user = (session?.user as any)?.id
    ? (session?.user as User)
    : null;

  const token = (session as any)?.apiToken || null;

  const logout = () => nextAuthSignOut({ callbackUrl: "/" });

  return (
    <AuthContext.Provider
      value={{
        user,
        token: token,
        loading: status === "loading",
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <AuthInner>{children}</AuthInner>
    </SessionProvider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
