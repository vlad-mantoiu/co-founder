"use client";

import {
  createContext,
  useContext,
  useState,
  type ReactNode,
  type ButtonHTMLAttributes,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

// ──────────────────────────────────────────────────────────────────────────────
// Minimal AlertDialog matching shadcn API surface
// ──────────────────────────────────────────────────────────────────────────────

interface AlertDialogContextValue {
  open: boolean;
  setOpen: (v: boolean) => void;
}

const AlertDialogContext = createContext<AlertDialogContextValue>({
  open: false,
  setOpen: () => {},
});

function useAlertDialog() {
  return useContext(AlertDialogContext);
}

// ────────────────────────────────────────────────────────────────────────────

interface AlertDialogProps {
  open?: boolean;
  onOpenChange?: (v: boolean) => void;
  children: ReactNode;
}

export function AlertDialog({ open: controlledOpen, onOpenChange, children }: AlertDialogProps) {
  const [internalOpen, setInternalOpen] = useState(false);

  const open = controlledOpen !== undefined ? controlledOpen : internalOpen;
  const setOpen = (v: boolean) => {
    setInternalOpen(v);
    onOpenChange?.(v);
  };

  return (
    <AlertDialogContext.Provider value={{ open, setOpen }}>
      {children}
    </AlertDialogContext.Provider>
  );
}

// ────────────────────────────────────────────────────────────────────────────

interface AlertDialogTriggerProps {
  asChild?: boolean;
  children: ReactNode;
}

export function AlertDialogTrigger({ children, asChild }: AlertDialogTriggerProps) {
  const { setOpen } = useAlertDialog();

  if (asChild && typeof children === "object" && children !== null) {
    return (
      <span
        onClick={() => setOpen(true)}
        style={{ display: "contents" }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && setOpen(true)}
      >
        {children}
      </span>
    );
  }

  return (
    <button onClick={() => setOpen(true)}>
      {children}
    </button>
  );
}

// ────────────────────────────────────────────────────────────────────────────

export function AlertDialogContent({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const { open, setOpen } = useAlertDialog();

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />

          {/* Dialog */}
          <motion.div
            key="dialog"
            initial={{ opacity: 0, scale: 0.95, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 8 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            role="alertdialog"
            aria-modal="true"
            className={cn(
              "fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-white/10 bg-obsidian-light p-6 shadow-xl",
              className
            )}
          >
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// ────────────────────────────────────────────────────────────────────────────

export function AlertDialogHeader({ children }: { children: ReactNode }) {
  return <div className="space-y-2 mb-6">{children}</div>;
}

export function AlertDialogFooter({ children }: { children: ReactNode }) {
  return <div className="flex gap-3 justify-end mt-6">{children}</div>;
}

export function AlertDialogTitle({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <h2 className={cn("text-base font-semibold", className)}>{children}</h2>
  );
}

export function AlertDialogDescription({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p className={cn("text-sm text-white/60", className)}>{children}</p>
  );
}

// ────────────────────────────────────────────────────────────────────────────

interface AlertDialogActionProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  className?: string;
}

export function AlertDialogAction({ children, className, onClick, ...props }: AlertDialogActionProps) {
  const { setOpen } = useAlertDialog();

  return (
    <button
      {...props}
      className={cn(
        "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
        className
      )}
      onClick={(e) => {
        onClick?.(e);
        setOpen(false);
      }}
    >
      {children}
    </button>
  );
}

export function AlertDialogCancel({ children, className, ...props }: AlertDialogActionProps) {
  const { setOpen } = useAlertDialog();

  return (
    <button
      {...props}
      className={cn(
        "px-4 py-2 rounded-lg text-sm font-medium bg-white/5 border border-white/10 text-white hover:bg-white/10 transition-colors",
        className
      )}
      onClick={() => setOpen(false)}
    >
      {children}
    </button>
  );
}
