"use client";

import { useState } from "react";
import { Lock, ChevronDown, ChevronUp } from "lucide-react";
import type { ThesisSnapshot as ThesisSnapshotType } from "@/hooks/useOnboarding";

interface ThesisSnapshotProps {
  snapshot: ThesisSnapshotType;
  onEdit: (fieldName: string, newValue: string) => void;
  onCreateProject?: () => void;
  onStartFresh?: () => void;
}

/**
 * ThesisSnapshot: Hybrid card summary + expandable full document view.
 *
 * Features:
 * - Card summary with core fields (truncated)
 * - Expandable to full document view
 * - Inline editing with optimistic updates
 * - Tier-gated sections with upgrade prompts
 */
export function ThesisSnapshot({
  snapshot,
  onEdit,
  onCreateProject,
  onStartFresh,
}: ThesisSnapshotProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const startEditing = (fieldName: string, currentValue: string) => {
    setEditingField(fieldName);
    setEditValue(currentValue);
  };

  const saveEdit = () => {
    if (editingField && editValue.trim()) {
      onEdit(editingField, editValue.trim());
    }
    setEditingField(null);
    setEditValue("");
  };

  const cancelEdit = () => {
    setEditingField(null);
    setEditValue("");
  };

  const renderField = (
    label: string,
    fieldName: keyof ThesisSnapshotType,
    value: string | string[] | null | undefined,
    isLocked: boolean = false,
    lockedTier?: string,
  ) => {
    // Tier-gated section
    if (isLocked || value === null || value === undefined) {
      return (
        <div className="space-y-3 p-4 bg-white/5 border border-white/10 rounded-xl relative overflow-hidden">
          <div className="absolute inset-0 bg-white/5 backdrop-blur-sm" />
          <div className="relative z-10 flex items-start gap-3">
            <Lock className="w-5 h-5 text-brand mt-0.5" />
            <div className="flex-1 space-y-2">
              <h4 className="font-semibold text-white">{label}</h4>
              <p className="text-sm text-muted-foreground">
                Unlock deeper insights about {label.toLowerCase()} with {lockedTier} plan
              </p>
              <a
                href="/billing"
                className="inline-block px-4 py-2 text-sm bg-brand hover:bg-brand/90 text-white font-medium rounded-lg transition-colors"
              >
                Upgrade to {lockedTier}
              </a>
            </div>
          </div>
        </div>
      );
    }

    const displayValue = Array.isArray(value) ? value : String(value);
    const isEditing = editingField === fieldName;

    return (
      <div className="space-y-2 p-4 bg-white/5 border border-white/10 rounded-xl">
        <div className="flex items-center justify-between">
          <h4 className="font-semibold text-white">{label}</h4>
          {!isEditing && (
            <button
              onClick={() => startEditing(fieldName, Array.isArray(displayValue) ? displayValue.join("\n") : displayValue)}
              className="px-3 py-1 text-xs text-brand hover:text-brand/80 font-medium transition-colors"
            >
              Edit
            </button>
          )}
        </div>

        {isEditing ? (
          <div className="space-y-2">
            <textarea
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              className="w-full min-h-24 px-3 py-2 bg-white/10 border border-white/10 rounded-lg text-white placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent resize-none"
              rows={4}
              autoFocus
            />
            <div className="flex items-center gap-2">
              <button
                onClick={saveEdit}
                className="px-4 py-1.5 bg-brand hover:bg-brand/90 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Save
              </button>
              <button
                onClick={cancelEdit}
                className="px-4 py-1.5 text-muted-foreground hover:text-white text-sm font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : Array.isArray(displayValue) ? (
          <ul className="space-y-1.5 text-muted-foreground">
            {displayValue.map((item, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-brand mt-1">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground">{displayValue}</p>
        )}
      </div>
    );
  };

  // Card summary view
  if (!isExpanded) {
    return (
      <div className="space-y-6">
        <div className="space-y-4 p-6 bg-white/5 border border-white/10 rounded-xl">
          <h3 className="text-2xl font-display font-bold text-white">
            Your Thesis Snapshot
          </h3>

          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Problem</p>
              <p className="text-white line-clamp-2">{snapshot.problem}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Target User</p>
              <p className="text-white line-clamp-1">{snapshot.target_user}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Value Proposition</p>
              <p className="text-white line-clamp-2">{snapshot.value_prop}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Key Constraint</p>
              <p className="text-white line-clamp-1">{snapshot.key_constraint}</p>
            </div>
          </div>

          <button
            onClick={() => setIsExpanded(true)}
            className="flex items-center gap-2 text-brand hover:text-brand/80 font-medium transition-colors"
          >
            View Full Snapshot
            <ChevronDown className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-3">
          {onCreateProject && (
            <button
              onClick={onCreateProject}
              className="flex-1 px-6 py-3 bg-brand hover:bg-brand/90 text-white font-medium rounded-xl transition-colors"
            >
              Create Project
            </button>
          )}
          {onStartFresh && (
            <button
              onClick={onStartFresh}
              className="px-6 py-3 text-muted-foreground hover:text-white font-medium transition-colors"
            >
              Start Fresh
            </button>
          )}
        </div>
      </div>
    );
  }

  // Full document view
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-3xl font-display font-bold text-white">
          Your Thesis Snapshot
        </h3>
        <button
          onClick={() => setIsExpanded(false)}
          className="flex items-center gap-2 text-brand hover:text-brand/80 font-medium transition-colors"
        >
          Collapse
          <ChevronUp className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-4">
        {/* Core fields (always present) */}
        {renderField("Problem", "problem", snapshot.problem)}
        {renderField("Target User", "target_user", snapshot.target_user)}
        {renderField("Value Proposition", "value_prop", snapshot.value_prop)}
        {renderField("Key Constraint", "key_constraint", snapshot.key_constraint)}

        {/* Business fields (Partner+) */}
        {renderField(
          "Differentiation",
          "differentiation",
          snapshot.differentiation,
          !snapshot.differentiation,
          "Partner"
        )}
        {renderField(
          "Monetization Hypothesis",
          "monetization_hypothesis",
          snapshot.monetization_hypothesis,
          !snapshot.monetization_hypothesis,
          "Partner"
        )}

        {/* Strategic fields (CTO) */}
        {renderField(
          "Assumptions",
          "assumptions",
          snapshot.assumptions,
          !snapshot.assumptions,
          "CTO"
        )}
        {renderField(
          "Risks",
          "risks",
          snapshot.risks,
          !snapshot.risks,
          "CTO"
        )}
        {renderField(
          "Smallest Viable Experiment",
          "smallest_viable_experiment",
          snapshot.smallest_viable_experiment,
          !snapshot.smallest_viable_experiment,
          "CTO"
        )}
      </div>

      <div className="flex items-center gap-3">
        {onCreateProject && (
          <button
            onClick={onCreateProject}
            className="flex-1 px-6 py-3 bg-brand hover:bg-brand/90 text-white font-medium rounded-xl transition-colors"
          >
            Create Project
          </button>
        )}
        {onStartFresh && (
          <button
            onClick={onStartFresh}
            className="px-6 py-3 text-muted-foreground hover:text-white font-medium transition-colors"
          >
            Start Fresh
          </button>
        )}
      </div>
    </div>
  );
}
