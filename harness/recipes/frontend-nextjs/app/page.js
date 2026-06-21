"use client";
// Disable SSR for the chat app — it uses browser-only APIs (localStorage, fetch on mount).
import dynamic from "next/dynamic";

const ChatApp = dynamic(() => import("./ChatApp"), { ssr: false });

export default function Page() {
  return <ChatApp />;
}
