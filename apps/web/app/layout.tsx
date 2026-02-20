import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "LexiBel — AI-Native Legal Practice Management",
  description: "Plateforme de gestion de cabinet d'avocats avec IA pour le Barreau belge",
  viewport: "width=device-width, initial-scale=1, maximum-scale=1",
  themeColor: "#1E293B",
  icons: {
    icon: "/favicon.ico",
    apple: "/apple-touch-icon.png",
  },
  manifest: "/manifest.json",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
