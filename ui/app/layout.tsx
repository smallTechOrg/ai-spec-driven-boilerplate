export const metadata = {
  title: "Support Triage Agent",
  description: "Classify a support ticket by urgency + category and draft a suggested reply.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0 }}>{children}</body>
    </html>
  );
}
