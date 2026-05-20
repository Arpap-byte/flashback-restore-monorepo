import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'

const isPublicRoute = createRouteMatcher([
  '/',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/auth(.*)',
  '/about',
  '/privacy',
  '/terms',
  '/cookies',
  '/conditions-utilisation',
  '/mentions-legales',
  '/credits',
  '/bibliotheque',
  '/historique',
  '/dashboard',
  '/restore',
  '/animate',
  '/abonnement(.*)',
  '/business',
  '/blog',
  '/blog/(.*)',
  '/api/public(.*)',
])

export default clerkMiddleware(async (auth, request) => {
  if (!isPublicRoute(request)) {
    const authObj = await auth()
    if (!authObj.userId) {
      // Redirection explicite vers /sign-in (évite le rewrite Clerk qui cause 404)
      const signInUrl = new URL('/sign-in', request.url)
      return NextResponse.redirect(signInUrl)
    }
  }
})

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest|json|xml|txt)).*)',
    '/(api|trpc)(.*)',
  ],
}
