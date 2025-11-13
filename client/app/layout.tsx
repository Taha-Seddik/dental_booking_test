import "./globals.css";
import type { Metadata } from "next";
import { AuthProvider } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: "Dental AI Chatbot",
  description: "Appointment scheduling assistant",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-100 min-h-screen">
        <AuthProvider>
          <Providers>
            <Navbar />
            <main className="max-w-4xl mx-auto px-4 py-6">{children}</main>
          </Providers>
        </AuthProvider>
      </body>
    </html>
  );
}
