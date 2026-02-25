"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Lock, ArrowRight, Mail } from "lucide-react";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const LAUNCH_DATE = new Date("2026-03-15T00:00:00Z");
const TOTAL_DISCOUNT_SPOTS = 200;
const CLAIMED_SPOTS = 36; // Starting claimed — bump as real signups come in

const CITIES = [
  { name: "San Francisco", code: "SF", gradient: "from-indigo-500 to-purple-600" },
  { name: "London", code: "LD", gradient: "from-emerald-500 to-teal-600" },
  { name: "Berlin", code: "BE", gradient: "from-orange-500 to-red-600" },
  { name: "Tokyo", code: "TK", gradient: "from-blue-500 to-cyan-600" },
  { name: "Sydney", code: "SY", gradient: "from-pink-500 to-rose-600" },
  { name: "Toronto", code: "TO", gradient: "from-violet-500 to-fuchsia-600" },
  { name: "Singapore", code: "SG", gradient: "from-teal-500 to-emerald-600" },
  { name: "Amsterdam", code: "AM", gradient: "from-amber-500 to-orange-600" },
  { name: "Dubai", code: "DU", gradient: "from-cyan-500 to-blue-600" },
  { name: "Austin", code: "AU", gradient: "from-red-500 to-pink-600" },
  { name: "Stockholm", code: "ST", gradient: "from-sky-500 to-indigo-600" },
  { name: "Mumbai", code: "MU", gradient: "from-yellow-500 to-amber-600" },
];

const ACTIONS = [
  (city: string) => `A founder in ${city} just joined.`,
  (city: string) => `New sign-up from ${city}.`,
  (city: string) => `${city} founder joined the waitlist.`,
  (city: string) => `Early access claimed from ${city}.`,
];

const MAP_MARKERS = [
  { top: "30%", left: "22%", delay: "0s" },     // SF
  { top: "33%", left: "30%", delay: "0.5s" },    // East US
  { top: "28%", left: "47%", delay: "1.2s" },    // UK
  { top: "32%", left: "51%", delay: "0.8s" },    // Europe
  { top: "45%", left: "78%", delay: "1.5s" },    // Asia
  { top: "55%", left: "82%", delay: "0.3s" },    // SE Asia
  { top: "65%", left: "85%", delay: "1.8s" },    // Australia
  { top: "40%", left: "60%", delay: "2.1s" },    // Middle East
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
// Ticker hook — cycles through fake social proof entries
// ---------------------------------------------------------------------------

interface TickerEntry {
  id: number;
  city: typeof CITIES[number];
  action: string;
  ago: string;
}

function useTicker() {
  const [entries, setEntries] = useState<TickerEntry[]>([]);

  useEffect(() => {
    // Seed initial entries
    const initial: TickerEntry[] = [
      { id: 0, city: CITIES[0], action: ACTIONS[0](CITIES[0].name), ago: "2 seconds ago" },
      { id: 1, city: CITIES[1], action: ACTIONS[1](CITIES[1].name), ago: "45 seconds ago" },
      { id: 2, city: CITIES[2], action: ACTIONS[2](CITIES[2].name), ago: "2 minutes ago" },
      { id: 3, city: CITIES[3], action: ACTIONS[3](CITIES[3].name), ago: "5 minutes ago" },
    ];
    setEntries(initial);

    let counter = 4;
    const id = setInterval(() => {
      const city = CITIES[counter % CITIES.length];
      const action = ACTIONS[counter % ACTIONS.length](city.name);
      const entry: TickerEntry = { id: counter, city, action, ago: "just now" };
      counter++;
      setEntries((prev) => [entry, ...prev].slice(0, 6));
    }, 8000);

    return () => clearInterval(id);
  }, []);

  return entries;
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

function TickerItem({ entry, index }: { entry: TickerEntry; index: number }) {
  const opacities = [1, 0.8, 0.6, 0.4, 0.25, 0.15];
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: opacities[index] ?? 0.15, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="flex items-start gap-3 p-3 rounded-lg bg-white/5 border border-white/5 transition-all hover:bg-white/10"
    >
      <div
        className={`h-8 w-8 rounded-full bg-gradient-to-br ${entry.city.gradient} flex items-center justify-center text-xs font-bold text-white shrink-0`}
      >
        {entry.city.code}
      </div>
      <div className="min-w-0">
        <p className="text-sm text-white/70 leading-snug">{entry.action}</p>
        <p className="text-xs text-white/30 mt-0.5">{entry.ago}</p>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function WaitlistContent() {
  const countdown = useCountdown(LAUNCH_DATE);
  const ticker = useTicker();
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const spotsRemaining = TOTAL_DISCOUNT_SPOTS - CLAIMED_SPOTS;
  const progressPercent = (CLAIMED_SPOTS / TOTAL_DISCOUNT_SPOTS) * 100;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || submitting) return;
    setSubmitting(true);

    // Simulate API call — wire to real endpoint later
    await new Promise((r) => setTimeout(r, 800));
    setSubmitted(true);
    setSubmitting(false);
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
            <span className="text-glow">Inner Circle</span>
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
                    <svg className="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-white font-semibold text-lg mb-1">
                    You&apos;re in.
                  </p>
                  <p className="text-white/50 text-sm">
                    Check your inbox for confirmation. Welcome to the Inner Circle.
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

            {!submitted && (
              <p className="mt-4 text-xs text-white/30 flex items-center gap-1.5">
                <Lock className="h-3.5 w-3.5" />
                Encrypted &amp; secure. No spam, ever.
              </p>
            )}
          </motion.div>
        </div>
      </div>

      {/* ---- Right Column: Map & Social Proof ---- */}
      <div className="lg:w-[45%] xl:w-[40%] relative min-h-[500px] lg:min-h-auto flex flex-col bg-obsidian-light border-l border-white/5">
        {/* World map background */}
        <div
          className="absolute inset-0 bg-cover bg-center opacity-50 mix-blend-lighten"
          style={{ backgroundImage: "url('/images/world-map.png')" }}
        />

        {/* Gradient overlay for depth */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-obsidian/20 to-obsidian pointer-events-none" />

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

        {/* Social proof ticker */}
        <div className="relative z-10 flex-1 flex flex-col justify-end p-6 lg:p-10 pb-20">
          <div className="glass-strong rounded-2xl p-1 border border-white/5 overflow-hidden max-w-sm ml-auto">
            {/* Header */}
            <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
              <span className="text-xs font-bold text-white/40 uppercase tracking-wider">
                Live Activity
              </span>
              <div className="flex items-center gap-1.5">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-brand" />
                </span>
                <span className="text-xs text-brand font-medium">24 active</span>
              </div>
            </div>

            {/* Entries */}
            <div className="flex flex-col gap-2 p-3 max-h-[280px] overflow-hidden relative">
              <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-obsidian-light to-transparent z-10" />
              <AnimatePresence initial={false}>
                {ticker.map((entry, i) => (
                  <TickerItem key={entry.id} entry={entry} index={i} />
                ))}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
