import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import Facebook from "next-auth/providers/facebook"
import Credentials from "next-auth/providers/credentials"
import { SignJWT } from "jose"

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://148.230.116.52:8000"

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
    }),
    Facebook({
      clientId: process.env.AUTH_FACEBOOK_ID!,
      clientSecret: process.env.AUTH_FACEBOOK_SECRET!,
    }),
    Credentials({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Mot de passe", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null
        }

        try {
          const res = await fetch(`${BACKEND_URL}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          })

          if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            throw new Error(err.detail || "Email ou mot de passe incorrect.")
          }

          const data = await res.json()
          // Retourner l'id explicitement pour qu'il soit dans le JWT
          return {
            id: data.utilisateur.id,
            email: data.utilisateur.email,
            name: data.utilisateur.email.split("@")[0],
            backendToken: data.token,
          }
        } catch (error: any) {
          console.error("[Credentials] Erreur login:", error.message)
          return null
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account, user }) {
      if (account) {
        token.provider = account.provider
      }
      // Conserver l'id, le token backend et le nom
      if (user) {
        if ((user as any).backendToken) {
          token.backendToken = (user as any).backendToken
        }
        if ((user as any).id) {
          token.userId = (user as any).id
        }
        if (user.name) {
          token.name = user.name
        }
      }
      return token
    },
    async session({ session, token }) {
      // Injecter l'id et le nom dans session.user (obligatoire pour useAuth)
      if (session.user) {
        (session.user as any).id = token.userId || token.sub
        if (token.name) {
          session.user.name = token.name
        }
      }

      // Token backend JWT pour les appels API
      const rawToken = (token as any).backendToken
      if (rawToken) {
        (session as any).jwt = rawToken
      } else {
        // Fallback OAuth: encoder un JWT
        const secret = new TextEncoder().encode(process.env.AUTH_SECRET!)
        const jwtString = await new SignJWT({
          email: token.email,
          sub: token.sub,
          name: token.name,
          provider: token.provider,
        })
          .setProtectedHeader({ alg: "HS256" })
          .setIssuedAt()
          .setExpirationTime("24h")
          .sign(secret)
        ;(session as any).jwt = jwtString
      }

      return session
    },
  },
  pages: {
    signIn: "/auth",
  },
  trustHost: true,
})
