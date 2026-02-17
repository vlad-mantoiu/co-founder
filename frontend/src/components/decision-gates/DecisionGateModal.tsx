"use client";

import { X } from "lucide-react";
import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { GateOptionCard } from "./GateOptionCard";
import { NarrowPivotForm } from "./NarrowPivotForm";
import type { GateOption } from "@/hooks/useDecisionGate";

interface BriefSummary {
  problem_statement?: string;
  target_user?: string;
  value_prop?: string;
}

interface DecisionGateModalProps {
  isOpen: boolean;
  onClose: () => void;
  gateId: string | null;
  projectId: string;
  briefSummary?: BriefSummary;
  options: GateOption[];
  selectedOption: string | null;
  onSelectOption: (value: string) => void;
  onResolve: (actionText?: string, parkNote?: string) => void;
  isResolving: boolean;
  error: string | null;
}

/**
 * Full-screen Decision Gate 1 modal.
 *
 * Layout:
 * - Header with title and subtitle
 * - Brief context panel (problem, target, value prop)
 * - 2x2 grid of GateOptionCard components
 * - Conditional forms for narrow/pivot/park
 * - Footer with Cancel + Confirm Decision buttons
 *
 * Full attention: blocks everything, Escape key closes.
 */
export function DecisionGateModal({
  isOpen,
  onClose,
  projectId,
  briefSummary,
  options,
  selectedOption,
  onSelectOption,
  onResolve,
  isResolving,
  error,
}: DecisionGateModalProps) {
  const [narrowPivotText, setNarrowPivotText] = useState("");
  const [parkNote, setParkNote] = useState("");

  // Handle Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !isResolving) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden"; // Prevent background scroll
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [isOpen, isResolving, onClose]);

  const handleConfirm = () => {
    if (!selectedOption) return;

    if (selectedOption === "narrow" || selectedOption === "pivot") {
      onResolve(narrowPivotText);
    } else if (selectedOption === "park") {
      onResolve(undefined, parkNote);
    } else {
      onResolve();
    }
  };

  if (!isOpen) return null;

  const canConfirm =
    selectedOption &&
    !(
      (selectedOption === "narrow" || selectedOption === "pivot") &&
      !narrowPivotText.trim()
    );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-7xl h-screen max-h-screen flex flex-col bg-obsidian border border-white/10 shadow-2xl">
        {/* Header */}
        <div className="p-8 pb-6 border-b border-white/5">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h2 className="text-3xl font-display text-white">
                Decision Gate 1: Direction
              </h2>
              <p className="text-muted-foreground mt-2">
                This is a critical decision point. Review your Idea Brief, then
                choose your path forward.
              </p>
            </div>
            <button
              onClick={onClose}
              disabled={isResolving}
              className="p-2 rounded-lg text-muted-foreground hover:text-white hover:bg-white/5 transition-colors disabled:opacity-50"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Brief context panel */}
        {briefSummary && (
          <div className="px-8 py-4 bg-white/5 border-b border-white/5">
            <h4 className="text-sm font-semibold text-white mb-2">
              Your Current Brief
            </h4>
            <div className="text-xs text-muted-foreground space-y-1">
              {briefSummary.problem_statement && (
                <p>
                  <strong className="text-white">Problem:</strong>{" "}
                  {briefSummary.problem_statement.slice(0, 100)}
                  {briefSummary.problem_statement.length > 100 ? "..." : ""}
                </p>
              )}
              {briefSummary.target_user && (
                <p>
                  <strong className="text-white">Target:</strong>{" "}
                  {briefSummary.target_user.slice(0, 100)}
                  {briefSummary.target_user.length > 100 ? "..." : ""}
                </p>
              )}
              {briefSummary.value_prop && (
                <p>
                  <strong className="text-white">Value:</strong>{" "}
                  {briefSummary.value_prop.slice(0, 100)}
                  {briefSummary.value_prop.length > 100 ? "..." : ""}
                </p>
              )}
            </div>
            <a
              href={`/project/${projectId}/brief`}
              className="text-xs text-brand mt-2 inline-block hover:underline"
            >
              View full brief →
            </a>
          </div>
        )}

        {/* Main content area */}
        <div className="flex-1 overflow-y-auto p-8">
          {/* Options grid */}
          <div className="grid grid-cols-2 gap-6 mb-6">
            {options.map((option) => (
              <GateOptionCard
                key={option.value}
                option={option}
                isSelected={selectedOption === option.value}
                onSelect={() => onSelectOption(option.value)}
              />
            ))}
          </div>

          {/* Conditional forms */}
          {(selectedOption === "narrow" || selectedOption === "pivot") && (
            <NarrowPivotForm
              type={selectedOption as "narrow" | "pivot"}
              value={narrowPivotText}
              onChange={setNarrowPivotText}
            />
          )}

          {selectedOption === "park" && (
            <div className="p-6 glass-strong rounded-2xl border border-white/5 space-y-3">
              <label className="block text-sm font-semibold text-white">
                Why are you parking this? (optional)
              </label>
              <textarea
                value={parkNote}
                onChange={(e) => setParkNote(e.target.value)}
                placeholder="E.g., Need to validate market first, timing not right, resource constraints..."
                rows={3}
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
              />
            </div>
          )}

          {/* Error display */}
          {error && (
            <div className="mt-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-8 pt-6 border-t border-white/5 flex items-center justify-between">
          <button
            onClick={onClose}
            disabled={isResolving}
            className={cn(
              "px-6 py-2.5 rounded-xl text-sm font-medium transition-colors",
              "text-muted-foreground hover:text-white hover:bg-white/5",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!canConfirm || isResolving}
            className={cn(
              "min-w-[200px] px-6 py-2.5 rounded-xl text-sm font-semibold transition-all",
              "bg-brand text-white shadow-glow",
              "hover:bg-brand/90",
              "disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
            )}
          >
            {isResolving ? "Confirming..." : "Confirm Decision"}
          </button>
        </div>
      </div>
    </div>
  );
}
