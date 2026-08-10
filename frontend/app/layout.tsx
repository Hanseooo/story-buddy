import type { Metadata } from "next";
import { Outfit, Inter, JetBrains_Mono, Nunito } from "next/font/google";
import OfflineIndicator from "@/components/OfflineIndicator";
import "./globals.css";

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

const nunito = Nunito({
  variable: "--font-kid",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "StoryBuddy",
  description: "An AI-powered storyboarding and picture-book generation system.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${outfit.variable} ${inter.variable} ${jetbrainsMono.variable} ${nunito.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col font-sans text-foreground bg-background selection:bg-primary selection:text-on-primary">
        <OfflineIndicator />
        {children}
      </body>
    </html>
  );
}
