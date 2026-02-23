import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isProtectedRoute = createRouteMatcher([
  "/dashboard(.*)",
  "/onboarding(.*)",
  "/projects(.*)",
  "/billing(.*)",
  "/chat(.*)",
  "/company(.*)",
  "/strategy(.*)",
  "/timeline(.*)",
  "/understanding(.*)",
  "/architecture(.*)",
  "/admin(.*)",
]);

export default clerkMiddleware(async (auth, request) => {
  const { pathname } = request.nextUrl;

  // Root redirect — auth-aware, check pathname first to avoid running auth() on every request
  if (pathname === "/") {
    const { userId } = await auth();
    if (userId) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
    return NextResponse.redirect(new URL("/sign-in", request.url));
  }

  // Admin: require auth + admin role
  if (pathname.startsWith("/admin")) {
    const { userId, sessionClaims } = await auth();
    const isAdmin =
      (sessionClaims?.publicMetadata as Record<string, unknown>)?.admin === true;
    if (!userId || !isAdmin) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
    return;
  }

  // All other protected routes
  if (isProtectedRoute(request)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals, static files, and backend proxy path
    "/((?!_next|backend|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
