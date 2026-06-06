import type { Metadata } from "next";
import { Exo_2, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const exo2 = Exo_2({
  variable: "--font-display",
  subsets: ["latin"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-mono",
  weight: ["400", "500"],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Library Client",
  description: "Next.js клиент для Обозревателя Технической Документации",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className={`${exo2.variable} ${plexMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
