import type { Metadata } from "next";
import "./globals.css";
import ClientProviders from "./ClientProviders";

export const metadata: Metadata = {
  title: {
    default: "Bhudi RMM",
    template: "%s · Bhudi RMM",
  },
  description:
    "AI-powered IT operations platform — monitor, manage, and secure endpoints for MSPs and enterprise IT.",
  icons: {
    icon: [{ url: "/brand/bhudi-mark.svg", type: "image/svg+xml" }],
    apple: "/brand/bhudi-logo.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <ClientProviders>{children}</ClientProviders>
      </body>
    </html>
  );
}
