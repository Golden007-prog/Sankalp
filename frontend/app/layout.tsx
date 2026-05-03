import type { Metadata, Viewport } from "next";
import "./globals.css";
import { TooltipProvider } from "@/components/ui/tooltip";
import { LanguageProvider } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "Sankalp",
  description: "Your democracy, decoded. In your language.",
  applicationName: "Sankalp",
};

export const viewport: Viewport = {
  themeColor: "#0a0a0a",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <a href="#main" className="skip-link">Skip to main content</a>
        <LanguageProvider>
          <TooltipProvider delayDuration={200}>{children}</TooltipProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
