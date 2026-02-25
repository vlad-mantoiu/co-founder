"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Lock, ArrowRight, Mail } from "lucide-react";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const LAUNCH_DATE = new Date("2026-03-15T00:00:00Z");
const TOTAL_DISCOUNT_SPOTS = 200;
const CLAIMED_SPOTS = 36;

const FORMSUBMIT_URL =
  "https://formsubmit.co/ajax/002df2771de3e721afa6f861db2fdf4a";

const MAP_MARKERS = [
  { top: "30%", left: "22%", delay: "0s" },
  { top: "33%", left: "30%", delay: "0.5s" },
  { top: "28%", left: "47%", delay: "1.2s" },
  { top: "32%", left: "51%", delay: "0.8s" },
  { top: "45%", left: "78%", delay: "1.5s" },
  { top: "55%", left: "82%", delay: "0.3s" },
  { top: "65%", left: "85%", delay: "1.8s" },
  { top: "40%", left: "60%", delay: "2.1s" },
];

// ---------------------------------------------------------------------------
// Countdown hook
// ---------------------------------------------------------------------------

function useCountdown(target: Date) {
  const calc = useCallback(() => {
    const diff = Math.max(0, target.getTime() - Date.now());
    return {
      days: Math.floor(diff / 86400000),
      hours: Math.floor((diff % 86400000) / 3600000),
      mins: Math.floor((diff % 3600000) / 60000),
      secs: Math.floor((diff % 60000) / 1000),
    };
  }, [target]);

  const [time, setTime] = useState(calc);

  useEffect(() => {
    const id = setInterval(() => setTime(calc()), 1000);
    return () => clearInterval(id);
  }, [calc]);

  return time;
}

// ---------------------------------------------------------------------------
// SVG World Map (dot-matrix style, indigo-themed)
// ---------------------------------------------------------------------------

function WorldMapSvg() {
  return (
    <svg
      viewBox="0 0 1000 500"
      className="w-full h-full opacity-40"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <radialGradient id="dot-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#6467f2" stopOpacity="0.6" />
          <stop offset="100%" stopColor="#6467f2" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="map-vignette" cx="50%" cy="50%" r="60%">
          <stop offset="0%" stopColor="transparent" />
          <stop offset="100%" stopColor="#050505" />
        </radialGradient>
      </defs>
      {/* Grid lines */}
      <g stroke="#6467f2" strokeOpacity="0.06" strokeWidth="0.5" fill="none">
        {[...Array(13)].map((_, i) => (
          <line key={`h${i}`} x1="0" y1={i * 40} x2="1000" y2={i * 40} />
        ))}
        {[...Array(26)].map((_, i) => (
          <line key={`v${i}`} x1={i * 40} y1="0" x2={i * 40} y2="500" />
        ))}
      </g>
      {/* Simplified continent dots */}
      <g fill="#6467f2" fillOpacity="0.35">
        {/* North America */}
        {[
          [180,100],[200,100],[220,100],[200,120],[220,120],[240,120],
          [160,120],[180,120],[200,140],[220,140],[240,140],[260,140],
          [180,140],[200,160],[220,160],[240,160],[180,160],[160,160],
          [200,180],[220,180],[240,180],[260,180],[280,180],
          [220,200],[240,200],[260,200],[280,200],[300,200],
          [240,220],[260,220],[280,220],[240,240],[260,240],
        ].map(([cx, cy], i) => (
          <circle key={`na${i}`} cx={cx} cy={cy} r="3" />
        ))}
        {/* South America */}
        {[
          [300,260],[320,260],[300,280],[320,280],[340,280],
          [300,300],[320,300],[340,300],[300,320],[320,320],[340,320],
          [320,340],[340,340],[320,360],[340,360],[320,380],[340,380],
          [320,400],[340,400],[330,420],
        ].map(([cx, cy], i) => (
          <circle key={`sa${i}`} cx={cx} cy={cy} r="3" />
        ))}
        {/* Europe */}
        {[
          [460,100],[480,100],[500,100],[460,120],[480,120],[500,120],[520,120],
          [440,140],[460,140],[480,140],[500,140],[520,140],
          [460,160],[480,160],[500,160],[520,160],[540,160],
          [460,180],[480,180],[500,180],[520,180],
        ].map(([cx, cy], i) => (
          <circle key={`eu${i}`} cx={cx} cy={cy} r="3" />
        ))}
        {/* Africa */}
        {[
          [480,200],[500,200],[520,200],[500,220],[520,220],[540,220],
          [500,240],[520,240],[540,240],[560,240],
          [500,260],[520,260],[540,260],[560,260],
          [520,280],[540,280],[560,280],[520,300],[540,300],[560,300],
          [540,320],[560,320],[540,340],[560,340],
        ].map(([cx, cy], i) => (
          <circle key={`af${i}`} cx={cx} cy={cy} r="3" />
        ))}
        {/* Asia */}
        {[
          [560,100],[580,100],[600,100],[620,100],[640,100],[660,100],
          [560,120],[580,120],[600,120],[620,120],[640,120],[660,120],[680,120],
          [580,140],[600,140],[620,140],[640,140],[660,140],[680,140],[700,140],
          [600,160],[620,160],[640,160],[660,160],[680,160],[700,160],[720,160],
          [620,180],[640,180],[660,180],[680,180],[700,180],[720,180],[740,180],
          [640,200],[660,200],[680,200],[700,200],[720,200],
          [660,220],[680,220],[700,220],[720,220],[740,220],
          [700,240],[720,240],[740,240],
        ].map(([cx, cy], i) => (
          <circle key={`as${i}`} cx={cx} cy={cy} r="3" />
        ))}
        {/* Australia */}
        {[
          [780,300],[800,300],[820,300],[840,300],
          [780,320],[800,320],[820,320],[840,320],[860,320],
          [800,340],[820,340],[840,340],[860,340],
          [820,360],[840,360],
        ].map(([cx, cy], i) => (
          <circle key={`au${i}`} cx={cx} cy={cy} r="3" />
        ))}
      </g>
      {/* Vignette overlay */}
      <rect width="1000" height="500" fill="url(#map-vignette)" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CountdownUnit({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex h-16 w-16 sm:h-20 sm:w-20 items-center justify-center rounded-xl glass border-white/10 bg-gradient-to-br from-white/5 to-transparent">
        <span className="text-2xl sm:text-3xl font-bold font-mono tabular-nums">
          {String(value).padStart(2, "0")}
        </span>
      </div>
      <span className="text-[10px] text-center text-white/40 uppercase tracking-widest">
        {label}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function WaitlistContent() {
  const countdown = useCountdown(LAUNCH_DATE);
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const spotsRemaining = TOTAL_DISCOUNT_SPOTS - CLAIMED_SPOTS;
  const progressPercent = (CLAIMED_SPOTS / TOTAL_DISCOUNT_SPOTS) * 100;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || submitting) return;
    setSubmitting(true);
    setError("");

    try {
      const res = await fetch(FORMSUBMIT_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          email,
          _subject: `Co-Founder.ai Waitlist: ${email}`,
          _template: "table",
          source: "waitlist-page",
          timestamp: new Date().toISOString(),
        }),
      });

      if (!res.ok) throw new Error("Submission failed");
      setSubmitted(true);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col lg:flex-row min-h-[calc(100vh-140px)]">
      {/* ---- Left Column: Content & Form ---- */}
      <div className="flex-1 flex flex-col justify-center p-6 lg:p-16 xl:p-24 relative overflow-hidden">
        {/* Decorative glow */}
        <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-brand/20 rounded-full blur-[120px] -translate-x-1/2 -translate-y-1/2 pointer-events-none" />

        <div className="max-w-2xl relative z-10 pt-16 lg:pt-0">
          {/* Status badge */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold uppercase tracking-wider mb-8"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
            </span>
            Waitlist Open
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-4xl sm:text-6xl lg:text-7xl font-black leading-[1.1] tracking-tight mb-6"
          >
            Join the <br />
            <span className="text-brand text-glow">Inner Circle</span>
          </motion.h1>

          {/* Sub-headline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-white/50 text-lg sm:text-xl leading-relaxed mb-10 max-w-lg"
          >
            The first 200 founders to join get{" "}
            <span className="text-white font-semibold">50% off</span> their first
            3 months. Don&apos;t wait for the launch&mdash;lead it.
          </motion.p>

          {/* Countdown */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex gap-3 sm:gap-4 mb-12"
          >
            <CountdownUnit value={countdown.days} label="Days" />
            <CountdownUnit value={countdown.hours} label="Hours" />
            <CountdownUnit value={countdown.mins} label="Mins" />
            <CountdownUnit value={countdown.secs} label="Secs" />
          </motion.div>

          {/* Signup card */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="glass-card-strong p-6 sm:p-8 rounded-2xl max-w-lg"
          >
            {/* Progress bar */}
            <div className="flex justify-between items-end mb-3">
              <p className="text-sm font-medium text-white/60">
                Discount spots remaining
              </p>
              <p className="text-emerald-400 font-mono font-bold text-sm">
                {spotsRemaining}/{TOTAL_DISCOUNT_SPOTS}
              </p>
            </div>
            <div className="h-2 w-full bg-white/5 rounded-full mb-6 overflow-hidden">
              <div
                className="h-full bg-emerald-500 glow-green rounded-full relative transition-all duration-1000"
                style={{ width: `${100 - progressPercent}%` }}
              >
                <div className="absolute inset-0 bg-white/20 animate-shimmer" />
              </div>
            </div>

            <AnimatePresence mode="wait">
              {submitted ? (
                <motion.div
                  key="success"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="text-center py-4"
                >
                  <div className="h-12 w-12 mx-auto mb-3 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
                    <svg
                      className="h-6 w-6 text-emerald-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2.5}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </div>
                  <p className="text-white font-semibold text-lg mb-1">
                    You&apos;re in.
                  </p>
                  <p className="text-white/50 text-sm">
                    Check your inbox for confirmation. Welcome to the Inner
                    Circle.
                  </p>
                </motion.div>
              ) : (
                <motion.form
                  key="form"
                  onSubmit={handleSubmit}
                  className="flex flex-col sm:flex-row gap-3"
                >
                  <div className="relative flex-grow group">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-white/30 group-focus-within:text-brand transition-colors">
                      <Mail className="h-5 w-5" />
                    </div>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="founder@company.com"
                      className="w-full bg-white/5 border border-white/10 text-white text-sm rounded-xl focus:ring-2 focus:ring-brand focus:border-transparent block pl-10 p-3.5 placeholder-white/30 transition-all outline-none h-12"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="bg-brand hover:bg-brand-dark text-white font-bold py-3 px-6 rounded-xl transition-all shadow-glow hover:shadow-glow-lg h-12 whitespace-nowrap flex items-center justify-center gap-2 disabled:opacity-60"
                  >
                    <span>{submitting ? "Joining..." : "Secure Access"}</span>
                    {!submitting && <ArrowRight className="h-4 w-4" />}
                  </button>
                </motion.form>
              )}
            </AnimatePresence>

            {error && (
              <p className="mt-3 text-xs text-red-400">{error}</p>
            )}

            {!submitted && (
              <p className="mt-4 text-xs text-white/30 flex items-center gap-1.5">
                <Lock className="h-3.5 w-3.5" />
                Encrypted &amp; secure. No spam, ever.
              </p>
            )}
          </motion.div>
        </div>
      </div>

      {/* ---- Right Column: Globe Map ---- */}
      <div className="lg:w-[45%] xl:w-[40%] relative min-h-[400px] lg:min-h-auto flex flex-col bg-obsidian-light border-l border-white/5 overflow-hidden">
        {/* SVG world map */}
        <div className="absolute inset-0 flex items-center justify-center p-8">
          <WorldMapSvg />
        </div>

        {/* Gradient overlay for depth */}
        <div className="absolute inset-0 bg-gradient-to-b from-obsidian/40 via-transparent to-obsidian pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-r from-obsidian/60 via-transparent to-obsidian/40 pointer-events-none" />

        {/* Pulsing map markers */}
        {MAP_MARKERS.map((marker, i) => (
          <div
            key={i}
            className="map-pulse"
            style={{
              top: marker.top,
              left: marker.left,
              animationDelay: marker.delay,
            }}
          />
        ))}

        {/* Center label */}
        <div className="absolute inset-0 flex items-end justify-center pb-16 pointer-events-none">
          <p className="text-white/20 text-xs uppercase tracking-[0.3em] font-medium">
            Founders joining worldwide
          </p>
        </div>
      </div>
    </div>
  );
}
