import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that require authentication
const PROTECTED_PREFIXES = ['/', '/certificates', '/claims', '/documents', '/billing', '/quotes', '/organization'];

// Routes that should redirect to dashboard if already authenticated
const AUTH_ROUTES = ['/login', '/register'];

// Routes that are always accessible
const PUBLIC_PREFIXES = ['/quote', '/api', '/_next', '/favicon'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Always allow public routes and static assets
  if (PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return NextResponse.next();
  }

  // Check for auth cookie (set by the client when tokens are stored)
  const hasAuth = request.cookies.get('corgi_auth')?.value === '1';

  // Auth routes: redirect to dashboard if already authenticated
  // But preserve redirect param — if an SSO redirect is in progress, allow through
  if (AUTH_ROUTES.includes(pathname)) {
    const redirectParam = request.nextUrl.searchParams.get('redirect');
    if (hasAuth && !redirectParam) {
      return NextResponse.redirect(new URL('/', request.url));
    }
    return NextResponse.next();
  }

  // Protected routes: redirect to the portal's own /login page if not
  // authenticated. The portal owns its auth flow — no external SSO bounce.
  const isProtected = pathname === '/' || PROTECTED_PREFIXES.some((prefix) => prefix !== '/' && pathname.startsWith(prefix));
  if (isProtected && !hasAuth) {
    // Build an absolute URL so NextResponse.redirect keeps the client's
    // public host + port (x-forwarded-*). Next.js standalone behind nginx
    // otherwise leaks the internal HOSTNAME:PORT into request.url.
    const forwardedHost = request.headers.get('x-forwarded-host') ?? request.headers.get('host') ?? request.nextUrl.host;
    const forwardedProto = request.headers.get('x-forwarded-proto') ?? request.nextUrl.protocol.replace(':', '');
    const loginUrl = new URL('/login', `${forwardedProto}://${forwardedHost}`);
    if (pathname !== '/') {
      loginUrl.searchParams.set('redirect', pathname);
    }
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all paths except static files and Next.js internals
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
