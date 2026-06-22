"use client";

interface StubBannerProps {
  stubMode: boolean;
}

export function StubBanner({ stubMode }: StubBannerProps) {
  if (!stubMode) return null;
  return (
    <div
      role="alert"
      className="w-full bg-amber-100 border-b border-amber-300 text-amber-900 px-4 py-3 text-sm"
    >
      <strong>Stub mode:</strong> Gemini API key not configured. Set the{" "}
      <code className="font-mono bg-amber-200 px-1 rounded">GEMINI_API_KEY</code>{" "}
      environment variable and restart the server to enable natural-language queries.
    </div>
  );
}
