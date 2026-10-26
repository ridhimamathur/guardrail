import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "GuardRAIL · Runtime Security", description: "Runtime trust and authorization for enterprise AI agents" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
