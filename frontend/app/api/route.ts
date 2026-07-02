// frontend/app/api/auth/[...nextauth]/route.ts
import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        // Demo credentials - replace with real database check later
        if (credentials?.email === "admin@bhudi.com" && credentials?.password === "admin123") {
          return {
            id: "1",
            name: "Admin User",
            email: credentials.email,
            role: "admin"
          };
        }
        return null;
      }
    })
  ],
  pages: {
    signIn: "/login",
  },
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, user }) {
      if (user) (token as any).role = (user as any).role;
      return token;
    },
    async session({ session, token }) {
      if (token) {
        (session.user as any).id = token.sub as string;
        (session.user as any).role = token.role as string;
      }
      return session;
    },
  },
});