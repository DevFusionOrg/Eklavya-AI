import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Eklavya.AI",
  description: "Scholarship and fellowship management for Scheduled Tribes",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

