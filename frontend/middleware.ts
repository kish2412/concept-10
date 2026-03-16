/** Route protection is delegated to Clerk; clinic onboarding is handled client-side. */
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isProtected = createRouteMatcher([
  "/patients(.*)",
  "/encounters(.*)",
  "/medications(.*)",
  "/settings(.*)",
  "/queue(.*)",
  "/admin(.*)",
]);

const isSelectClinic = createRouteMatcher(["/select-clinic(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (isProtected(req) || isSelectClinic(req)) {
    await auth.protect();
  }

  const { userId } = await auth();
  if (req.nextUrl.pathname === "/" && userId) {
    return NextResponse.redirect(new URL("/patients", req.url));
  }
});

export const config = {
  matcher: [
    "/",
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
