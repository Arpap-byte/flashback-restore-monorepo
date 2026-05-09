import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import Facebook from "next-auth/providers/facebook"
import { SignJWT } from "jose"

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
  ],
  callbacks: {
    async jwt({ token, account }) {
      if (account) {
        token.provider = account.provider;
      }
      return token;
    },
    async session({ session, token }) {
      // Encode the JWT using jose (same algo as backend: HS256)
      const secret = new TextEncoder().encode(process.env.AUTH_SECRET!);
      const jwtString = await new SignJWT({
        email: token.email,
        sub: token.sub,
        name: token.name,
        provider: token.provider,
      })
        .setProtectedHeader({ alg: "HS256" })
        .setIssuedAt()
        .setExpirationTime("24h")
        .sign(secret);

      (session as any).jwt = jwtString;
      return session;
    },
  },
  pages: {
    signIn: "/auth",
  },
})
