import { Navbar } from "@/components/marketing/navbar";
import { Footer } from "@/components/marketing/footer";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="font-display min-h-screen bg-obsidian text-white">
      <Navbar />
      <main>{children}</main>
      <Footer />
    </div>
  );
}
