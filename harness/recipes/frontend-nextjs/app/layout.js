import "./globals.css";

export const metadata = {
  title: "appname",
  description: "Agent chat starter",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  );
}
