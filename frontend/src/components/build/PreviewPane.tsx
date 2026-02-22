"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  AlertTriangle,
  Clock,
  ExternalLink,
  Loader2,
  Moon,
} from "lucide-react";
import { usePreviewPane } from "@/hooks/usePreviewPane";
import { BrowserChrome } from "./BrowserChrome";
import { cn } from "@/lib/utils";

// ──────────────────────────────────────────────────────────────────────────────
// Props
// ──────────────────────────────────────────────────────────────────────────────

interface PreviewPaneProps {
  previewUrl: string;
  sandboxExpiresAt: string | null;
  sandboxPaused: boolean;
  jobId: string;
  projectId: string;
  getToken: () => Promise<string | null>;
  onRebuild: () => void;
  onIterate: () => void;
  className?: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// Shared iframe attributes
// ──────────────────────────────────────────────────────────────────────────────

const IFRAME_SANDBOX =
  "allow-scripts allow-same-origin allow-forms allow-popups";
const IFRAME_ALLOW = "clipboard-read; clipboard-write";

// ──────────────────────────────────────────────────────────────────────────────
// Internal sub-components
// ──────────────────────────────────────────────────────────────────────────────

function CenteredOverlay({ children }: { children: React.ReactNode }) {
  return (
    <div className="w-full h-[600px] min-h-[400px] flex flex-col items-center justify-center gap-4 p-8">
      {children}
    </div>
  );
}

function StatusHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-base font-semibold text-white text-center">
      {children}
    </h3>
  );
}

function StatusSubtext({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-sm text-white/50 text-center max-w-xs leading-relaxed">
      {children}
    </p>
  );
}

function ActionButton({
  onClick,
  variant = "primary",
  children,
}: {
  onClick: () => void;
  variant?: "primary" | "secondary";
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
        variant === "primary"
          ? "bg-brand hover:bg-brand/90 text-white shadow-glow"
          : "border border-white/20 text-white/70 hover:bg-white/5 hover:text-white",
      )}
    >
      {children}
    </button>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// State-specific render helpers
// ──────────────────────────────────────────────────────────────────────────────

function CheckingView() {
  return (
    <CenteredOverlay>
      <Loader2 className="w-7 h-7 text-white/40 animate-spin" />
      <StatusSubtext>Checking preview...</StatusSubtext>
    </CenteredOverlay>
  );
}

function LoadingView({
  previewUrl,
  onLoad,
}: {
  previewUrl: string;
  onLoad: () => void;
}) {
  return (
    <div className="relative w-full h-[600px] min-h-[400px]">
      {/* Hidden iframe — loads in background, fires onLoad → markLoaded */}
      <iframe
        src={previewUrl}
        onLoad={onLoad}
        className="absolute inset-0 w-full h-full border-0 opacity-0"
        sandbox={IFRAME_SANDBOX}
        allow={IFRAME_ALLOW}
      />
      {/* Visible spinner overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
        <Loader2 className="w-7 h-7 text-white/40 animate-spin" />
        <StatusSubtext>Starting your app...</StatusSubtext>
      </div>
    </div>
  );
}

function ActiveView({
  previewUrl,
}: {
  previewUrl: string;
}) {
  return (
    <motion.iframe
      src={previewUrl}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.35 }}
      className="w-full h-[600px] min-h-[400px] border-0"
      sandbox={IFRAME_SANDBOX}
      allow={IFRAME_ALLOW}
    />
  );
}

function BlockedView({
  previewUrl,
  blockReason,
}: {
  previewUrl: string;
  blockReason: string | null;
}) {
  return (
    <CenteredOverlay>
      <AlertTriangle className="w-8 h-8 text-yellow-400" />
      <div className="text-center space-y-1.5">
        <StatusHeading>Preview can&apos;t load inline</StatusHeading>
        <StatusSubtext>
          The app&apos;s security headers prevent embedding. You can still view
          it in a new tab.
        </StatusSubtext>
        {blockReason && (
          <p className="text-white/30 font-mono text-xs mt-2">{blockReason}</p>
        )}
      </div>
      <button
        onClick={() => window.open(previewUrl, "_blank")}
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-brand hover:bg-brand/90 text-white text-sm font-medium transition-colors shadow-glow"
      >
        <ExternalLink className="w-4 h-4" />
        Open in new tab
      </button>
    </CenteredOverlay>
  );
}

function ExpiredView({
  onRebuild,
  onIterate,
}: {
  onRebuild: () => void;
  onIterate: () => void;
}) {
  return (
    <CenteredOverlay>
      <Clock className="w-8 h-8 text-white/40" />
      <div className="text-center space-y-1.5">
        <StatusHeading>Sandbox expired</StatusHeading>
        <StatusSubtext>
          Your preview sandbox has timed out. You can rebuild with the same
          configuration or iterate on this build.
        </StatusSubtext>
      </div>
      <div className="flex items-center gap-3">
        <ActionButton onClick={onRebuild} variant="primary">
          Rebuild as-is
        </ActionButton>
        <ActionButton onClick={onIterate} variant="secondary">
          Iterate on this build
        </ActionButton>
      </div>
    </CenteredOverlay>
  );
}

function ErrorView({
  previewUrl,
  onRetry,
}: {
  previewUrl: string;
  onRetry: () => void;
}) {
  return (
    <CenteredOverlay>
      <AlertCircle className="w-8 h-8 text-red-400/80" />
      <div className="text-center space-y-1.5">
        <StatusHeading>Unable to load preview</StatusHeading>
        <StatusSubtext>
          We couldn&apos;t connect to your preview. You can retry or open it
          directly.
        </StatusSubtext>
      </div>
      <div className="flex items-center gap-3">
        <ActionButton onClick={onRetry} variant="primary">
          Retry
        </ActionButton>
        <ActionButton
          onClick={() => window.open(previewUrl, "_blank")}
          variant="secondary"
        >
          <ExternalLink className="w-4 h-4" />
          Open in new tab
        </ActionButton>
      </div>
    </CenteredOverlay>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// New paused / resuming / resume_failed views
// ──────────────────────────────────────────────────────────────────────────────

function PausedView({ onResume }: { onResume: () => void }) {
  return (
    <CenteredOverlay>
      <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center">
        <Moon className="w-5 h-5 text-white/40" />
      </div>
      <div className="text-center space-y-1.5">
        <StatusHeading>Your preview is sleeping.</StatusHeading>
      </div>
      <ActionButton onClick={onResume} variant="primary">
        Resume preview
      </ActionButton>
    </CenteredOverlay>
  );
}

function ResumingView() {
  return (
    <CenteredOverlay>
      <Loader2 className="w-7 h-7 text-white/40 animate-spin" />
      <StatusSubtext>Resuming preview...</StatusSubtext>
    </CenteredOverlay>
  );
}

function ResumeFailedView({
  errorType,
  onRebuild,
}: {
  errorType: "sandbox_expired" | "sandbox_unreachable" | null;
  onRebuild: () => void;
}) {
  const message =
    errorType === "sandbox_expired"
      ? "The sandbox has expired and can\u2019t be recovered."
      : "The sandbox couldn\u2019t be reached. It may be corrupted.";

  const handleRebuild = () => {
    if (window.confirm("This will use 1 build credit. Continue?")) {
      onRebuild();
    }
  };

  return (
    <CenteredOverlay>
      <AlertCircle className="w-8 h-8 text-red-400/80" />
      <div className="text-center space-y-1.5">
        <StatusHeading>Resume failed</StatusHeading>
        <StatusSubtext>{message}</StatusSubtext>
      </div>
      <ActionButton onClick={handleRebuild} variant="primary">
        Rebuild
      </ActionButton>
    </CenteredOverlay>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Main orchestrator
// ──────────────────────────────────────────────────────────────────────────────

export function PreviewPane({
  previewUrl,
  sandboxExpiresAt,
  sandboxPaused,
  jobId,
  projectId: _projectId,
  getToken,
  onRebuild,
  onIterate,
  className,
}: PreviewPaneProps) {
  const {
    state,
    deviceMode,
    setDeviceMode,
    previewUrl: activePreviewUrl,
    blockReason,
    markLoaded,
    onRetry,
    handleResume,
    resumeErrorType,
  } = usePreviewPane(previewUrl, sandboxExpiresAt, sandboxPaused, jobId, getToken);

  // ── States that always show the browser chrome ────────────────────────────
  const showChrome =
    state === "checking" || state === "loading" || state === "active" || state === "error";

  // ── States that show a full replacement card (no chrome) ──────────────────
  const showFullCard =
    state === "blocked" ||
    state === "expired" ||
    state === "paused" ||
    state === "resuming" ||
    state === "resume_failed";

  return (
    <div className={cn("w-full", className)}>
      <AnimatePresence mode="wait">
        {showChrome && (
          <motion.div
            key="chrome"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            <BrowserChrome
              previewUrl={activePreviewUrl}
              deviceMode={deviceMode}
              onDeviceModeChange={setDeviceMode}
            >
              <AnimatePresence mode="wait">
                {state === "checking" && (
                  <motion.div
                    key="checking"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <CheckingView />
                  </motion.div>
                )}

                {state === "loading" && (
                  <motion.div
                    key="loading"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <LoadingView previewUrl={activePreviewUrl} onLoad={markLoaded} />
                  </motion.div>
                )}

                {state === "active" && (
                  <motion.div
                    key="active"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <ActiveView previewUrl={activePreviewUrl} />
                  </motion.div>
                )}

                {state === "error" && (
                  <motion.div
                    key="error"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <ErrorView previewUrl={activePreviewUrl} onRetry={onRetry} />
                  </motion.div>
                )}
              </AnimatePresence>
            </BrowserChrome>
          </motion.div>
        )}

        {showFullCard && (
          <motion.div
            key="fullcard"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3 }}
            className="rounded-xl border border-white/10 bg-[#0c0c10] overflow-hidden"
          >
            {state === "blocked" && (
              <BlockedView previewUrl={activePreviewUrl} blockReason={blockReason} />
            )}
            {state === "expired" && (
              <ExpiredView onRebuild={onRebuild} onIterate={onIterate} />
            )}
            {state === "paused" && (
              <PausedView onResume={handleResume} />
            )}
            {state === "resuming" && (
              <ResumingView />
            )}
            {state === "resume_failed" && (
              <ResumeFailedView errorType={resumeErrorType} onRebuild={onRebuild} />
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
