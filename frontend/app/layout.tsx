import type { Metadata } from "next";
import "./globals.css";
import ClientProviders from "./ClientProviders";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://bhudi.online";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Bhudi",
    template: "%s · Bhudi",
  },
  description:
    "AI-powered IT help for your computer — remote support, monitoring, and a modern operations workspace.",
  applicationName: "Bhudi",
  authors: [{ name: "Bhudi", url: SITE_URL }],
  creator: "Bhudi",
  publisher: "Bhudi",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: SITE_URL,
    siteName: "Bhudi",
    title: "Bhudi",
    description:
      "Remote help for your PC — install once, stay connected, get assistance when you need it.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Bhudi",
    description:
      "Remote help for your PC — install once, stay connected, get assistance when you need it.",
  },
  alternates: {
    canonical: SITE_URL,
  },
  icons: {
    icon: [{ url: "/brand/bhudi-mark.svg", type: "image/svg+xml" }],
    apple: "/brand/bhudi-logo.png",
  },
  robots: {
    index: true,
    follow: true,
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
