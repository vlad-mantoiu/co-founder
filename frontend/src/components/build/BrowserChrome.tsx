"use client";

import { Copy, Monitor, Tablet, Smartphone, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

type DeviceMode = "desktop" | "tablet" | "mobile";

interface BrowserChromeProps {
  previewUrl: string;
  deviceMode: DeviceMode;
  onDeviceModeChange: (mode: DeviceMode) => void;
  children: React.ReactNode;
  className?: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// Device config
// ──────────────────────────────────────────────────────────────────────────────

const DEVICE_BUTTONS: {
  mode: DeviceMode;
  Icon: React.ElementType;
  label: string;
}[] = [
  { mode: "desktop", Icon: Monitor, label: "Desktop" },
  { mode: "tablet", Icon: Tablet, label: "Tablet" },
  { mode: "mobile", Icon: Smartphone, label: "Mobile" },
];

const DEVICE_MAX_WIDTH: Record<DeviceMode, string> = {
  desktop: "w-full",
  tablet: "max-w-[768px]",
  mobile: "max-w-[375px]",
};

// ──────────────────────────────────────────────────────────────────────────────
// Component
// ──────────────────────────────────────────────────────────────────────────────

export function BrowserChrome({
  previewUrl,
  deviceMode,
  onDeviceModeChange,
  children,
  className,
}: BrowserChromeProps) {
  async function handleCopyUrl() {
    try {
      await navigator.clipboard.writeText(previewUrl);
      toast.success("URL copied!");
    } catch {
      toast.error("Failed to copy URL");
    }
  }

  function handleOpenInNewTab() {
    window.open(previewUrl, "_blank");
  }

  return (
    <div
      className={cn(
        "rounded-xl border border-white/10 overflow-hidden bg-[#0c0c10]",
        className,
      )}
    >
      {/* Toolbar */}
      <div className="h-10 px-3 flex items-center justify-between bg-white/[0.03] border-b border-white/10">
        {/* Left: Window dots */}
        <div className="flex gap-1.5 flex-shrink-0">
          <span className="w-3 h-3 rounded-full bg-red-400/80" />
          <span className="w-3 h-3 rounded-full bg-yellow-400/80" />
          <span className="w-3 h-3 rounded-full bg-green-400/80" />
        </div>

        {/* Center: Copy URL */}
        <button
          onClick={handleCopyUrl}
          title="Copy preview URL"
          className="flex items-center gap-1.5 px-2 py-1 rounded text-white/40 hover:text-white/70 hover:bg-white/5 transition-colors text-xs"
        >
          <Copy className="w-3.5 h-3.5" />
          <span className="hidden sm:inline font-mono">Copy URL</span>
        </button>

        {/* Right: Device toggles + open in new tab */}
        <div className="flex items-center gap-0.5 flex-shrink-0">
          {DEVICE_BUTTONS.map(({ mode, Icon, label }) => (
            <button
              key={mode}
              onClick={() => onDeviceModeChange(mode)}
              title={label}
              className={cn(
                "p-1.5 rounded transition-colors",
                deviceMode === mode
                  ? "bg-white/10 text-white"
                  : "text-white/30 hover:text-white/60 hover:bg-white/5",
              )}
            >
              <Icon className="w-3.5 h-3.5" />
            </button>
          ))}

          {/* Divider */}
          <span className="w-px h-4 bg-white/10 mx-1" />

          {/* Open in new tab */}
          <button
            onClick={handleOpenInNewTab}
            title="Open in new tab"
            className="p-1.5 rounded text-white/30 hover:text-white/70 hover:bg-white/5 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Content area — device width constraint */}
      <div className="w-full flex justify-center overflow-hidden">
        <div
          className={cn(
            "w-full transition-all duration-300",
            DEVICE_MAX_WIDTH[deviceMode],
          )}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
