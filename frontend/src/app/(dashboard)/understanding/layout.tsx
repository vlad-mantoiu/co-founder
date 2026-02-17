/**
 * Understanding interview layout: Full-screen without BrandNav or sidebar.
 *
 * Matches Phase 4 onboarding layout for focused interview experience.
 */
export default function UnderstandingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-obsidian bg-grid">
      <main className="min-h-screen">{children}</main>
    </div>
  );
}
