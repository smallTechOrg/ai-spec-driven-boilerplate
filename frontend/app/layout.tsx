import type { Metadata } from "next";
import "./globals.css";
import SessionSidebar from "@/components/SessionSidebar";
import ErrorToastRegion from "@/components/ErrorToastRegion";
import { AppProvider } from "@/components/AppContext";

export const metadata: Metadata = {
  title: "Data Analyst Agent",
  description: "Natural-language data analysis with AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <AppProvider>
          {/* Stub-mode banner — hardcoded Phase 1; Phase 2 wires to /health */}
          <div className="w-full bg-yellow-300 text-center py-2 font-bold text-sm">
            STUB MODE — responses are canned, not real AI output
          </div>
          {/* Top nav */}
          <nav className="flex items-center px-4 py-3 bg-gray-800 text-white">
            <span className="font-bold text-lg">Data Analyst Agent</span>
            <div className="ml-6 flex gap-4 text-sm">
              <a href="/" className="hover:text-gray-300">Query</a>
              <a href="/datasets" className="hover:text-gray-300">Datasets</a>
            </div>
          </nav>
          {/* Main layout */}
          <div className="flex" style={{ height: "calc(100vh - 88px)" }}>
            {/* Sidebar */}
            <SessionSidebar />
            {/* Content */}
            <main className="flex-1 overflow-y-auto p-6">
              {children}
            </main>
          </div>
          {/* Error toast region */}
          <ErrorToastRegion />
        </AppProvider>
      </body>
    </html>
  );
}
