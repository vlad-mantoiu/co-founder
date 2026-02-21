"use client";

import { Mail, Clock, MessageCircle } from "lucide-react";
import { FadeIn } from "@/components/marketing/fade-in";

export default function ContactContent() {
  return (
    <>
      {/* Hero */}
      <section className="relative pt-32 pb-16 lg:pt-40 lg:pb-20 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-brand/8 rounded-full blur-[120px] pointer-events-none" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="hero-fade">
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight">
              Get in Touch
            </h1>
          </div>
          <div className="hero-fade-delayed">
            <p className="mt-4 text-lg text-white/50 max-w-xl mx-auto">
              Have a question about Co-Founder.ai? We would love to hear from you.
            </p>
          </div>
        </div>
      </section>

      {/* Contact Info */}
      <section className="pb-24 lg:pb-32">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <FadeIn>
            <div className="text-center mb-12">
              <a
                href="mailto:hello@getinsourced.ai"
                className="inline-flex items-center gap-3 px-8 py-4 bg-brand text-white font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg text-lg"
              >
                <Mail className="h-5 w-5" />
                hello@getinsourced.ai
              </a>
            </div>
          </FadeIn>

          <div className="grid sm:grid-cols-3 gap-6">
            {[
              {
                icon: Mail,
                title: "Email Us",
                text: "hello@getinsourced.ai",
              },
              {
                icon: Clock,
                title: "Response Time",
                text: "Within 24 hours on business days",
              },
              {
                icon: MessageCircle,
                title: "Live Chat",
                text: "Available for Pro and Enterprise plans",
              },
            ].map((item, i) => (
              <FadeIn key={item.title} delay={i * 0.1}>
                <div className="glass rounded-2xl p-6 text-center h-full">
                  <div className="h-10 w-10 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center mx-auto mb-4">
                    <item.icon className="h-5 w-5 text-brand" />
                  </div>
                  <h3 className="font-semibold text-sm mb-1">{item.title}</h3>
                  <p className="text-sm text-white/40">{item.text}</p>
                </div>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
