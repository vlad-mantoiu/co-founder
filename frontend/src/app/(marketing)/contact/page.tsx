"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Send, Mail, Clock, MessageCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { FadeIn } from "@/components/marketing/fade-in";

interface FormState {
  name: string;
  email: string;
  subject: string;
  message: string;
}

interface FormErrors {
  name?: string;
  email?: string;
  subject?: string;
  message?: string;
}

export default function ContactPage() {
  const [form, setForm] = useState<FormState>({
    name: "",
    email: "",
    subject: "",
    message: "",
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    document.title = "Contact | Co-Founder.ai";
  }, []);

  const validate = (): boolean => {
    const next: FormErrors = {};
    if (!form.name.trim()) next.name = "Name is required.";
    if (!form.email.trim()) {
      next.email = "Email is required.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      next.email = "Enter a valid email address.";
    }
    if (!form.subject.trim()) next.subject = "Please select a subject.";
    if (!form.message.trim()) {
      next.message = "Message is required.";
    } else if (form.message.trim().length < 10) {
      next.message = "Message must be at least 10 characters.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      setSubmitted(true);
    }
  };

  const update = (field: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  if (submitted) {
    return (
      <section className="pt-32 pb-24 lg:pt-40 lg:pb-32">
        <div className="max-w-xl mx-auto px-4 text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4 }}
          >
            <div className="h-16 w-16 rounded-2xl bg-neon-green/10 border border-neon-green/20 flex items-center justify-center mx-auto mb-6">
              <Send className="h-8 w-8 text-neon-green" />
            </div>
            <h1 className="text-3xl font-bold mb-4">Message Sent</h1>
            <p className="text-white/50 leading-relaxed">
              Thanks for reaching out. We typically respond within 24 hours on
              business days. Keep an eye on your inbox.
            </p>
          </motion.div>
        </div>
      </section>
    );
  }

  return (
    <>
      {/* Hero */}
      <section className="relative pt-32 pb-12 lg:pt-40 lg:pb-16 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-brand/8 rounded-full blur-[120px] pointer-events-none" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight">
              Get in Touch
            </h1>
            <p className="mt-4 text-lg text-white/50 max-w-xl mx-auto">
              Have a question about Co-Founder.ai? We would love to hear from
              you.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Form + Info */}
      <section className="pb-24 lg:pb-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-3 gap-12">
            {/* Form */}
            <FadeIn className="lg:col-span-2">
              <form
                onSubmit={handleSubmit}
                className="glass rounded-2xl p-6 sm:p-8 lg:p-10 space-y-6"
                noValidate
              >
                <div className="grid sm:grid-cols-2 gap-6">
                  <div>
                    <label
                      htmlFor="contact-name"
                      className="block text-sm font-medium mb-2"
                    >
                      Name
                    </label>
                    <input
                      id="contact-name"
                      type="text"
                      value={form.name}
                      onChange={(e) => update("name", e.target.value)}
                      className={cn(
                        "w-full bg-white/[0.03] border rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/25 focus:outline-none focus:ring-2 focus:ring-brand/50 transition-colors",
                        errors.name ? "border-red-500/50" : "border-white/10"
                      )}
                      placeholder="Your name"
                    />
                    {errors.name && (
                      <p className="mt-1.5 text-xs text-red-400">
                        {errors.name}
                      </p>
                    )}
                  </div>
                  <div>
                    <label
                      htmlFor="contact-email"
                      className="block text-sm font-medium mb-2"
                    >
                      Email
                    </label>
                    <input
                      id="contact-email"
                      type="email"
                      value={form.email}
                      onChange={(e) => update("email", e.target.value)}
                      className={cn(
                        "w-full bg-white/[0.03] border rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/25 focus:outline-none focus:ring-2 focus:ring-brand/50 transition-colors",
                        errors.email ? "border-red-500/50" : "border-white/10"
                      )}
                      placeholder="you@company.com"
                    />
                    {errors.email && (
                      <p className="mt-1.5 text-xs text-red-400">
                        {errors.email}
                      </p>
                    )}
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="contact-subject"
                    className="block text-sm font-medium mb-2"
                  >
                    Subject
                  </label>
                  <select
                    id="contact-subject"
                    value={form.subject}
                    onChange={(e) => update("subject", e.target.value)}
                    className={cn(
                      "w-full bg-white/[0.03] border rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-brand/50 transition-colors appearance-none",
                      errors.subject ? "border-red-500/50" : "border-white/10",
                      !form.subject && "text-white/25"
                    )}
                  >
                    <option value="" className="bg-obsidian-light">
                      Select a topic
                    </option>
                    <option value="general" className="bg-obsidian-light text-white">
                      General Inquiry
                    </option>
                    <option value="sales" className="bg-obsidian-light text-white">
                      Sales / Enterprise
                    </option>
                    <option value="support" className="bg-obsidian-light text-white">
                      Technical Support
                    </option>
                    <option value="partnership" className="bg-obsidian-light text-white">
                      Partnership
                    </option>
                  </select>
                  {errors.subject && (
                    <p className="mt-1.5 text-xs text-red-400">
                      {errors.subject}
                    </p>
                  )}
                </div>

                <div>
                  <label
                    htmlFor="contact-message"
                    className="block text-sm font-medium mb-2"
                  >
                    Message
                  </label>
                  <textarea
                    id="contact-message"
                    rows={5}
                    value={form.message}
                    onChange={(e) => update("message", e.target.value)}
                    className={cn(
                      "w-full bg-white/[0.03] border rounded-xl px-4 py-3 text-sm text-white placeholder:text-white/25 focus:outline-none focus:ring-2 focus:ring-brand/50 transition-colors resize-none",
                      errors.message ? "border-red-500/50" : "border-white/10"
                    )}
                    placeholder="Tell us how we can help..."
                  />
                  {errors.message && (
                    <p className="mt-1.5 text-xs text-red-400">
                      {errors.message}
                    </p>
                  )}
                </div>

                <button
                  type="submit"
                  className="inline-flex items-center gap-2 px-8 py-3.5 bg-brand text-white font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg"
                >
                  Send Message
                  <Send className="h-4 w-4" />
                </button>
              </form>
            </FadeIn>

            {/* Sidebar */}
            <FadeIn delay={0.15} className="space-y-6">
              {[
                {
                  icon: Mail,
                  title: "Email Us",
                  text: "hello@cofounder.helixcx.io",
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
              ].map((item) => (
                <div
                  key={item.title}
                  className="glass rounded-2xl p-6 flex items-start gap-4"
                >
                  <div className="h-10 w-10 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center flex-shrink-0">
                    <item.icon className="h-5 w-5 text-brand" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm mb-1">{item.title}</h3>
                    <p className="text-sm text-white/40">{item.text}</p>
                  </div>
                </div>
              ))}
            </FadeIn>
          </div>
        </div>
      </section>
    </>
  );
}
