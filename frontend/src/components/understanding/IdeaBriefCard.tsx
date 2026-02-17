"use client";

import { useState } from "react";
import { ChevronDown, Edit2, Check, X } from "lucide-react";
import { ConfidenceIndicator } from "./ConfidenceIndicator";

interface IdeaBriefCardProps {
  section: {
    key: string;
    title: string;
    summary: string;
    fullContent: string | string[];
    confidence: "strong" | "moderate" | "needs_depth";
  };
  onEdit: (sectionKey: string, newContent: string) => void;
  isEditing?: boolean;
}

/**
 * IdeaBriefCard: Expandable card for one brief section.
 *
 * Collapsed: title + summary + confidence badge
 * Expanded: full content with inline editing
 * Manual expansion pattern matching Phase 4 onboarding.
 */
export function IdeaBriefCard({ section, onEdit, isEditing = false }: IdeaBriefCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editValue, setEditValue] = useState("");

  const handleEditClick = () => {
    const content = Array.isArray(section.fullContent)
      ? section.fullContent.join("\n")
      : section.fullContent;
    setEditValue(content);
    setIsEditMode(true);
  };

  const handleSave = () => {
    onEdit(section.key, editValue);
    setIsEditMode(false);
  };

  const handleCancel = () => {
    setIsEditMode(false);
    setEditValue("");
  };

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
      {/* Header - clickable to expand/collapse */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-start justify-between p-4 hover:bg-white/5 transition-colors text-left"
      >
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-3">
            <h4 className="text-base font-semibold text-white">{section.title}</h4>
            <ConfidenceIndicator confidence={section.confidence} />
          </div>
          {!isOpen && (
            <p className="text-sm text-muted-foreground line-clamp-2">{section.summary}</p>
          )}
        </div>
        <ChevronDown
          className={`h-5 w-5 text-muted-foreground shrink-0 transition-transform ml-4 ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Expanded content */}
      {isOpen && (
        <div className="px-4 pb-4 space-y-4 border-t border-white/10 pt-4">
          {isEditMode ? (
            // Edit mode: controlled textarea
            <div className="space-y-3">
              <textarea
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                className="w-full min-h-32 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent resize-y"
                rows={6}
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSave}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-brand hover:bg-brand/90 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  <Check className="h-4 w-4" />
                  Save
                </button>
                <button
                  onClick={handleCancel}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  <X className="h-4 w-4" />
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            // View mode: full content with edit button
            <div className="space-y-3">
              {Array.isArray(section.fullContent) ? (
                <ul className="space-y-1.5">
                  {section.fullContent.map((item, idx) => (
                    <li key={idx} className="text-sm text-white/90 flex gap-2">
                      <span className="text-muted-foreground">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-white/90 whitespace-pre-wrap">
                  {section.fullContent}
                </p>
              )}
              <button
                onClick={handleEditClick}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 text-white text-sm font-medium rounded-lg transition-colors"
              >
                <Edit2 className="h-4 w-4" />
                Edit inline
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
