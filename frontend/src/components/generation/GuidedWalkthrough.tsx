"use client";

import { useState } from "react";
import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, ExternalLink } from "lucide-react";
import Link from "next/link";

export interface WalkthroughStep {
  title: string;
  description: string;
  href: string;
  icon: React.ReactNode;
  preview?: React.ReactNode;
}

interface GuidedWalkthroughProps {
  projectId: string;
  steps: WalkthroughStep[];
  onComplete: () => void;
}

function StepDot({
  index,
  current,
  total,
}: {
  index: number;
  current: number;
  total: number;
}) {
  const isActive = index === current;
  const isPast = index < current;

  return (
    <div
      className={`rounded-full transition-all duration-300 ${
        isActive
          ? "w-6 h-2 bg-brand"
          : isPast
            ? "w-2 h-2 bg-brand/50"
            : "w-2 h-2 bg-white/20"
      }`}
    />
  );
}

export function GuidedWalkthrough({
  steps,
  onComplete,
}: GuidedWalkthroughProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState<"forward" | "back">("forward");

  const step = steps[currentStep];
  const isLast = currentStep === steps.length - 1;

  const handleNext = () => {
    if (isLast) {
      onComplete();
    } else {
      setDirection("forward");
      setCurrentStep((prev) => prev + 1);
    }
  };

  const variants = {
    enter: (dir: "forward" | "back") => ({
      x: dir === "forward" ? 60 : -60,
      opacity: 0,
    }),
    center: {
      x: 0,
      opacity: 1,
    },
    exit: (dir: "forward" | "back") => ({
      x: dir === "forward" ? -60 : 60,
      opacity: 0,
    }),
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <motion.div
        className="relative max-w-lg w-full mx-4 bg-[#0f0f14] border border-white/10 rounded-2xl p-8 shadow-2xl"
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        {/* Step dots */}
        <div className="flex justify-center gap-2 mb-8">
          {steps.map((_, i) => (
            <StepDot key={i} index={i} current={currentStep} total={steps.length} />
          ))}
        </div>

        {/* Step counter */}
        <p className="text-xs text-white/30 text-center mb-4 font-mono">
          {currentStep + 1} of {steps.length}
        </p>

        {/* Step content — animated slide */}
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={currentStep}
            custom={direction}
            variants={variants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="space-y-5"
          >
            {/* Icon */}
            <div className="flex justify-center">
              <div className="w-16 h-16 rounded-2xl bg-brand/10 border border-brand/20 flex items-center justify-center text-brand">
                {step.icon}
              </div>
            </div>

            {/* Title */}
            <h2 className="text-2xl font-display font-bold text-white text-center">
              {step.title}
            </h2>

            {/* Description */}
            <p className="text-sm text-white/60 text-center leading-relaxed">
              {step.description}
            </p>

            {/* Optional preview */}
            {step.preview && (
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
                {step.preview}
              </div>
            )}

            {/* View full link */}
            <div className="flex justify-center">
              <Link
                href={step.href}
                className="inline-flex items-center gap-1.5 text-sm text-brand hover:text-brand/80 transition-colors"
              >
                View full {step.title.replace("Here's your ", "")}
                <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <div className="mt-8">
          <button
            onClick={handleNext}
            className="w-full py-3 px-6 bg-brand hover:bg-brand/90 text-white font-semibold rounded-xl transition-all duration-200 shadow-glow flex items-center justify-center gap-2"
          >
            {isLast ? (
              "Go to Dashboard"
            ) : (
              <>
                Next
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
