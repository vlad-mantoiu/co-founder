import type { Metadata } from "next";
import Link from "next/link";
import { Terminal, ArrowRight } from "lucide-react";

export const metadata: Metadata = {
  title: "Sign In",
  description: "Sign in to your Co-Founder.ai account to continue building.",
};

export default function SignInPage() {
  return (
    <section className="pt-32 pb-24 lg:pt-40 lg:pb-32">
      <div className="max-w-md mx-auto px-4">
        <div className="glass rounded-2xl p-8 sm:p-10 text-center">
          <div className="h-14 w-14 rounded-2xl bg-brand/10 border border-brand/20 flex items-center justify-center mx-auto mb-6">
            <Terminal className="h-7 w-7 text-brand" />
          </div>

          <h1 className="text-2xl font-bold mb-2">Welcome Back</h1>
          <p className="text-sm text-white/40 mb-8">
            Sign in to your Co-Founder.ai account to continue building.
          </p>

          <Link
            href="/sign-in"
            className="flex items-center justify-center gap-2 w-full py-3.5 bg-brand text-white font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg"
          >
            Sign In to Your Account
            <ArrowRight className="h-4 w-4" />
          </Link>

          <div className="mt-6 pt-6 border-t border-white/5">
            <p className="text-sm text-white/40">
              New to Co-Founder.ai?{" "}
              <Link
                href="/sign-up"
                className="text-brand hover:text-brand-light transition-colors font-medium"
              >
                Create an account
              </Link>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
