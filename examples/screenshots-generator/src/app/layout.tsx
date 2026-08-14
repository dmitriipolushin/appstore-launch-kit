import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "App Store Screenshots — Product Scanner",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body style={{ fontFamily: "ui-rounded, -apple-system, system-ui, sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
