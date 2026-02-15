import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "LexiBel",
  description: "AI-Native Legal Practice Management for Belgian Bar",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
