"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { Plus, Github, ExternalLink, FolderOpen, X } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { GlassCard } from "@/components/ui/glass-card";

interface Project {
  id: string;
  name: string;
  description: string;
  github_repo: string | null;
  status: string;
  created_at: string;
}

export default function ProjectsPage() {
  const { getToken } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [newProject, setNewProject] = useState({ name: "", description: "" });

  useEffect(() => {
    async function fetchProjects() {
      try {
        const res = await apiFetch("/api/projects", getToken);
        if (res.ok) {
          const data = await res.json();
          setProjects(Array.isArray(data) ? data : []);
        }
      } catch {
        // API may not be running
      }
    }
    fetchProjects();
  }, [getToken]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProject.name.trim()) return;

    try {
      const response = await apiFetch("/api/projects", getToken, {
        method: "POST",
        body: JSON.stringify(newProject),
      });

      if (response.ok) {
        const project = await response.json();
        setProjects((prev) => [...prev, project]);
        setNewProject({ name: "", description: "" });
        setIsCreating(false);
      }
    } catch (error) {
      console.error("Failed to create project:", error);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-white">
            Your Projects
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage your repositories and project settings
          </p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand text-white text-sm font-medium hover:bg-brand-dark transition-colors shadow-glow self-start"
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      {/* Create project form */}
      {isCreating && (
        <GlassCard variant="strong" className="relative">
          <button
            onClick={() => setIsCreating(false)}
            className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground hover:text-white hover:bg-white/5 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>

          <h2 className="font-display font-semibold text-lg text-white mb-5">
            Create New Project
          </h2>

          <form onSubmit={handleCreateProject} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1.5">
                Project Name
              </label>
              <input
                type="text"
                value={newProject.name}
                onChange={(e) =>
                  setNewProject((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder="my-awesome-project"
                className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand/50 focus:border-transparent transition-all"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1.5">
                Description
              </label>
              <textarea
                value={newProject.description}
                onChange={(e) =>
                  setNewProject((prev) => ({
                    ...prev,
                    description: e.target.value,
                  }))
                }
                placeholder="What are you building?"
                rows={2}
                className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand/50 focus:border-transparent transition-all resize-none"
              />
            </div>
            <div className="flex gap-3 pt-1">
              <button
                type="submit"
                className="px-5 py-2.5 rounded-xl bg-brand text-white text-sm font-medium hover:bg-brand-dark transition-colors shadow-glow"
              >
                Create Project
              </button>
              <button
                type="button"
                onClick={() => setIsCreating(false)}
                className="px-5 py-2.5 rounded-xl border border-white/10 text-muted-foreground text-sm font-medium hover:text-white hover:bg-white/5 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </GlassCard>
      )}

      {/* Projects list */}
      {projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-brand/10 flex items-center justify-center mb-5">
            <FolderOpen className="w-8 h-8 text-brand" />
          </div>
          <h3 className="font-display text-xl font-semibold text-white mb-2">
            No projects yet
          </h3>
          <p className="text-muted-foreground mb-6 max-w-sm">
            Create your first project and your AI co-founder will be ready to start building.
          </p>
          {!isCreating && (
            <button
              onClick={() => setIsCreating(true)}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand text-white font-medium hover:bg-brand-dark transition-colors shadow-glow"
            >
              <Plus className="w-5 h-5" />
              Create Your First Project
            </button>
          )}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {projects.map((project) => (
            <GlassCard
              key={project.id}
              variant="strong"
              className="group hover:ring-1 hover:ring-brand/30 transition-all"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-display font-semibold text-white group-hover:text-brand transition-colors">
                    {project.name}
                  </h3>
                  {project.description && (
                    <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                      {project.description}
                    </p>
                  )}
                </div>
                <span
                  className={`flex-shrink-0 px-2.5 py-1 text-xs rounded-full font-medium ${
                    project.status === "active"
                      ? "bg-neon-green/10 text-neon-green"
                      : "bg-white/5 text-muted-foreground"
                  }`}
                >
                  {project.status}
                </span>
              </div>
              <div className="mt-4 flex items-center gap-3 text-xs text-muted-foreground">
                {project.github_repo && (
                  <a
                    href={`https://github.com/${project.github_repo}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 hover:text-brand transition-colors"
                  >
                    <Github className="w-3.5 h-3.5" />
                    {project.github_repo}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
                <span>
                  Created {new Date(project.created_at).toLocaleDateString()}
                </span>
              </div>
            </GlassCard>
          ))}
        </div>
      )}
    </div>
  );
}
