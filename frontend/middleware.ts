// frontend/middleware.ts
import { withAuth } from "next-auth/middleware";

export default withAuth(
  function middleware(req) {
    // Add role-based checks here later
  },
  {
    callbacks: {
      authorized: ({ token }) => !!token, // Require login
    },
  }
);

export const config = {
  matcher: ["/dashboard/:path*"], // Protect all dashboard routes
};