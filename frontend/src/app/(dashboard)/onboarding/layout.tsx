/**
 * Onboarding layout: Full-screen without BrandNav or sidebar.
 *
 * Provides minimal wrapper for focused onboarding flow.
 */
export default function OnboardingLayout({
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
