import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sankalp",
  description: "Your democracy, decoded. In your language.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-neutral-950 text-neutral-50 antialiased">
        {children}
      </body>
    </html>
  );
}
