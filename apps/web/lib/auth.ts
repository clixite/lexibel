import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

function getApiUrl(): string {
  return process.env.API_URL_INTERNAL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
}

const authConfig = NextAuth({
  providers: [
    Credentials({
      name: "LexiBel",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Mot de passe", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }

        try {
          const res = await fetch(`${getApiUrl()}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          });

          if (!res.ok) {
            return null;
          }

          const data = await res.json();

          // Decode JWT payload to extract user claims
          const payload = JSON.parse(
            Buffer.from(data.access_token.split(".")[1], "base64").toString()
          );

          return {
            id: payload.sub,
            email: payload.email,
            name: payload.email,
            role: payload.role,
            tenantId: payload.tid,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
          };
        } catch {
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        const u = user as any;
        token.id = u.id;
        token.email = u.email;
        token.name = u.name;
        token.role = u.role;
        token.tenantId = u.tenantId;
        token.accessToken = u.accessToken;
        token.refreshToken = u.refreshToken;
      }
      return token;
    },
    async session({ session, token }) {
      const t = token as any;
      (session.user as any) = {
        id: t.id || t.sub,
        email: t.email,
        name: t.name || t.email,
        role: t.role,
        tenantId: t.tenantId,
        accessToken: t.accessToken,
      };
      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
  },
  trustHost: true,
});

// Export only handlers for the API route — no server-side auth() in pages
export const { handlers, signIn, signOut } = authConfig;
