"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { apiFetch } from "@/lib/api";
import { RefreshCw, FileDown, FileText, Pencil, ChevronDown, ChevronUp, Save, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface ArtifactPanelProps {
  artifactId: string;
  projectId: string;
  onClose: () => void;
}

interface ArtifactContent {
  id: string;
  artifact_type: string;
  content: Record<string, unknown>;
  version_number: number;
  has_user_edits: boolean;
  generation_status: string;
  updated_at: string;
}

export function ArtifactPanel({ artifactId, onClose }: ArtifactPanelProps) {
  const { getToken } = useAuth();
  const [artifact, setArtifact] = useState<ArtifactContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [editMode, setEditMode] = useState(false);
  const [editedContent, setEditedContent] = useState<Record<string, string>>({});
  const [savingSection, setSavingSection] = useState<string | null>(null);

  // Fetch full artifact content on mount
  useEffect(() => {
    async function fetchArtifact() {
      try {
        setLoading(true);
        const response = await apiFetch(`/api/artifacts/${artifactId}`, getToken);

        if (!response.ok) {
          throw new Error(`Failed to fetch artifact: ${response.statusText}`);
        }

        const data: ArtifactContent = await response.json();
        setArtifact(data);

        // Expand first 2 sections by default
        const sections = Object.keys(data.content);
        setExpandedSections(new Set(sections.slice(0, 2)));

        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err : new Error("Failed to load artifact"));
      } finally {
        setLoading(false);
      }
    }

    fetchArtifact();
  }, [artifactId, getToken]);

  const toggleSection = (sectionKey: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sectionKey)) {
        next.delete(sectionKey);
      } else {
        next.add(sectionKey);
      }
      return next;
    });
  };

  const handleEditSection = (sectionKey: string, currentValue: string) => {
    setEditedContent((prev) => ({
      ...prev,
      [sectionKey]: currentValue,
    }));
  };

  const handleSaveSection = async (sectionKey: string) => {
    if (!artifact) return;

    try {
      setSavingSection(sectionKey);

      const response = await apiFetch(`/api/artifacts/${artifactId}/edit`, getToken, {
        method: "PATCH",
        body: JSON.stringify({
          section_path: sectionKey,
          new_content: editedContent[sectionKey],
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to save changes");
      }

      // Optimistic update
      setArtifact((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          content: {
            ...prev.content,
            [sectionKey]: editedContent[sectionKey],
          },
          has_user_edits: true,
        };
      });

      toast.success("Section saved successfully");
    } catch {
      toast.error("Failed to save section");
    } finally {
      setSavingSection(null);
    }
  };

  const handleRegenerate = async () => {
    try {
      const response = await apiFetch(`/api/artifacts/${artifactId}/regenerate`, getToken, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Failed to regenerate artifact");
      }

      toast.success("Regeneration started");
      onClose(); // Close panel and let dashboard polling show progress
    } catch {
      toast.error("Failed to start regeneration");
    }
  };

  const handleExportPDF = async () => {
    try {
      const response = await apiFetch(`/api/artifacts/${artifactId}/export/pdf`, getToken);

      if (!response.ok) {
        throw new Error("PDF export failed");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${artifact?.artifact_type || "artifact"}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success("PDF downloaded");
    } catch {
      toast.error("Failed to export PDF");
    }
  };

  const handleExportMarkdown = async () => {
    try {
      const response = await apiFetch(`/api/artifacts/${artifactId}/export/markdown`, getToken);

      if (!response.ok) {
        throw new Error("Markdown export failed");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${artifact?.artifact_type || "artifact"}.md`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success("Markdown downloaded");
    } catch {
      toast.error("Failed to export Markdown");
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <div className="space-y-3 animate-pulse">
          <div className="h-8 bg-white/10 rounded w-1/3" />
          <div className="h-4 bg-white/10 rounded w-full" />
          <div className="h-4 bg-white/10 rounded w-5/6" />
          <div className="h-4 bg-white/10 rounded w-4/6" />
        </div>
      </div>
    );
  }

  // Error state
  if (error || !artifact) {
    return (
      <div className="p-6 text-center space-y-4">
        <p className="text-red-400">Failed to load artifact.</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
        >
          Retry
        </button>
      </div>
    );
  }

  const sections = Object.entries(artifact.content);

  return (
    <div className="p-6 space-y-6">
      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={handleRegenerate}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-lg hover:bg-blue-500/20 transition"
        >
          <RefreshCw className="w-4 h-4" />
          Regenerate
        </button>

        <button
          onClick={handleExportPDF}
          className="flex items-center gap-2 px-4 py-2 bg-white/5 text-white/70 border border-white/10 rounded-lg hover:bg-white/10 transition"
        >
          <FileDown className="w-4 h-4" />
          Export PDF
        </button>

        <button
          onClick={handleExportMarkdown}
          className="flex items-center gap-2 px-4 py-2 bg-white/5 text-white/70 border border-white/10 rounded-lg hover:bg-white/10 transition"
        >
          <FileText className="w-4 h-4" />
          Export Markdown
        </button>

        <button
          onClick={() => setEditMode(!editMode)}
          className={`flex items-center gap-2 px-4 py-2 border rounded-lg transition ${
            editMode
              ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
              : "bg-white/5 text-white/70 border-white/10 hover:bg-white/10"
          }`}
        >
          <Pencil className="w-4 h-4" />
          {editMode ? "Exit Edit Mode" : "Edit"}
        </button>
      </div>

      {/* Content sections */}
      <div className="space-y-3">
        {sections.map(([key, value]) => {
          const isExpanded = expandedSections.has(key);
          const isEdited = editedContent[key] !== undefined;
          const isSaving = savingSection === key;
          const displayValue = isEdited ? editedContent[key] : String(value);

          return (
            <div
              key={key}
              className="bg-white/5 border border-white/10 rounded-lg overflow-hidden"
            >
              {/* Section header */}
              <button
                onClick={() => toggleSection(key)}
                className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-white/5 transition"
              >
                <h3 className="font-medium text-white capitalize">
                  {key.replace(/_/g, " ")}
                </h3>
                {isExpanded ? (
                  <ChevronUp className="w-5 h-5 text-white/50" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-white/50" />
                )}
              </button>

              {/* Section content */}
              {isExpanded && (
                <div className="px-4 py-3 border-t border-white/10">
                  {editMode ? (
                    <div className="space-y-3">
                      <textarea
                        value={displayValue}
                        onChange={(e) => handleEditSection(key, e.target.value)}
                        className="w-full min-h-[120px] p-3 bg-white/5 border border-white/10 rounded text-white/90 resize-y focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <button
                        onClick={() => handleSaveSection(key)}
                        disabled={isSaving || !isEdited}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isSaving ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Save className="w-4 h-4" />
                        )}
                        {isSaving ? "Saving..." : "Save"}
                      </button>
                    </div>
                  ) : (
                    <div className="prose prose-invert prose-sm max-w-none">
                      <p className="text-white/80 whitespace-pre-wrap">{displayValue}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
