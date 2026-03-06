import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isDashboardRoute = createRouteMatcher([
  "/patients(.*)",
  "/encounters(.*)",
  "/medications(.*)",
  "/settings(.*)",
]);
const isSelectClinicRoute = createRouteMatcher(["/select-clinic(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  const { userId, orgId } = await auth();

  if (req.nextUrl.pathname === "/" && userId) {
    const destination = orgId ? "/patients" : "/select-clinic";
    return NextResponse.redirect(new URL(destination, req.url));
  }

  if (isSelectClinicRoute(req)) {
    await auth.protect();
    if (orgId) {
      return NextResponse.redirect(new URL("/patients", req.url));
    }
    return;
  }

  if (isDashboardRoute(req)) {
    await auth.protect();
    if (!orgId) {
      return NextResponse.redirect(new URL("/select-clinic", req.url));
    }
  }
});

export const config = {
  matcher: [
    "/",
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
