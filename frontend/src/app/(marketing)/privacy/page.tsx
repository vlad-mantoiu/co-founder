import type { Metadata } from "next";
import { FadeIn } from "@/components/marketing/fade-in";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "Co-Founder.ai privacy policy. How we collect, use, and protect your personal data.",
};

export default function PrivacyPage() {
  return (
    <section className="pt-32 pb-24 lg:pt-40 lg:pb-32">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4">
            Privacy Policy
          </h1>
          <p className="text-white/40 text-sm mb-12">
            Last updated: February 15, 2026
          </p>
        </FadeIn>

        <div className="prose-invert space-y-10">
          <FadeIn delay={0.05}>
            <section>
              <h2 className="text-xl font-bold mb-3">1. Information We Collect</h2>
              <p className="text-sm text-white/50 leading-relaxed mb-3">
                We collect information you provide directly, including your name, email address,
                payment information, and any content you submit through our platform. We also
                collect usage data such as pages visited, features used, and session duration.
              </p>
              <p className="text-sm text-white/50 leading-relaxed">
                When you connect a GitHub repository, we access only the repositories you
                explicitly authorize. We do not access repositories outside your granted scope.
              </p>
            </section>
          </FadeIn>

          <FadeIn delay={0.08}>
            <section>
              <h2 className="text-xl font-bold mb-3">2. How We Use Your Information</h2>
              <p className="text-sm text-white/50 leading-relaxed mb-3">
                We use your information to provide and improve our services, process transactions,
                communicate with you, and ensure the security of your account. Your source code
                is processed solely to deliver the development services you request.
              </p>
              <p className="text-sm text-white/50 leading-relaxed">
                We do not use your code, project data, or any proprietary content to train
                machine learning models. Your intellectual property remains entirely yours.
              </p>
            </section>
          </FadeIn>

          <FadeIn delay={0.11}>
            <section>
              <h2 className="text-xl font-bold mb-3">3. Data Sharing</h2>
              <p className="text-sm text-white/50 leading-relaxed">
                We do not sell your personal information. We share data only with service
                providers necessary for operating our platform (payment processing, hosting
                infrastructure, email delivery). All service providers are contractually
                bound to protect your data and use it only for specified purposes.
              </p>
            </section>
          </FadeIn>

          <FadeIn delay={0.14}>
            <section>
              <h2 className="text-xl font-bold mb-3">4. Data Security</h2>
              <p className="text-sm text-white/50 leading-relaxed">
                All data is encrypted in transit using TLS 1.3 and at rest using AES-256
                encryption. We operate on SOC2-compliant infrastructure with regular security
                audits, access controls, and monitoring. Code execution happens in isolated
                sandbox environments that are destroyed after each session.
              </p>
            </section>
          </FadeIn>

          <FadeIn delay={0.17}>
            <section>
              <h2 className="text-xl font-bold mb-3">5. Data Retention</h2>
              <p className="text-sm text-white/50 leading-relaxed">
                We retain your account data for as long as your account is active. Project
                data and generated code are retained according to your subscription plan.
                Upon account deletion, all personal data is permanently removed within 30
                days. You can request a full data export at any time.
              </p>
            </section>
          </FadeIn>

          <FadeIn delay={0.2}>
            <section>
              <h2 className="text-xl font-bold mb-3">6. Your Rights</h2>
              <p className="text-sm text-white/50 leading-relaxed">
                You have the right to access, correct, export, or delete your personal data.
                You may also object to certain processing activities. To exercise any of
                these rights, contact us at privacy@cofounder.helixcx.io. We respond to all
                requests within 30 days.
              </p>
            </section>
          </FadeIn>

          <FadeIn delay={0.23}>
            <section>
              <h2 className="text-xl font-bold mb-3">7. Cookies</h2>
              <p className="text-sm text-white/50 leading-relaxed">
                We use essential cookies for authentication and session management. We use
                analytics cookies to understand how our platform is used. You can manage
                cookie preferences through your browser settings. Our platform functions
                with only essential cookies enabled.
              </p>
            </section>
          </FadeIn>

          <FadeIn delay={0.26}>
            <section>
              <h2 className="text-xl font-bold mb-3">8. Changes to This Policy</h2>
              <p className="text-sm text-white/50 leading-relaxed">
                We may update this policy from time to time. Significant changes will be
                communicated via email or an in-app notification. Continued use of our
                services after changes constitutes acceptance of the updated policy.
              </p>
            </section>
          </FadeIn>

          <FadeIn delay={0.29}>
            <section>
              <h2 className="text-xl font-bold mb-3">9. Contact</h2>
              <p className="text-sm text-white/50 leading-relaxed">
                For questions about this privacy policy or our data practices, contact us
                at privacy@cofounder.helixcx.io.
              </p>
            </section>
          </FadeIn>
        </div>
      </div>
    </section>
  );
}
