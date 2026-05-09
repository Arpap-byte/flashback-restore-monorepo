import { auth } from "@/auth"
import { NextResponse } from "next/server"

// Pages that require authentication
const PROTECTED = ["/restore", "/animate", "/historique", "/dashboard"]

export default auth((req) => {
  const { pathname } = req.nextUrl

  // Redirect to /auth if accessing protected page without session
  if (PROTECTED.some((p) => pathname.startsWith(p)) && !req.auth) {
    const url = new URL("/auth", req.url)
    url.searchParams.set("callbackUrl", pathname)
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
})

export const config = {
  matcher: ["/restore", "/animate", "/historique", "/dashboard"],
}
