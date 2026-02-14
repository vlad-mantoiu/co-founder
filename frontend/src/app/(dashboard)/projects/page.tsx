"use client";

import { useState } from "react";
import { Plus, Github, ExternalLink } from "lucide-react";

interface Project {
  id: string;
  name: string;
  description: string;
  github_repo: string | null;
  status: string;
  created_at: string;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [newProject, setNewProject] = useState({ name: "", description: "" });

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProject.name.trim()) return;

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/projects`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(newProject),
        }
      );

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
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">Projects</h1>
          <p className="text-muted-foreground">
            Manage your repositories and project settings
          </p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      {isCreating && (
        <div className="mb-6 p-4 rounded-lg border border-border bg-card">
          <h2 className="font-semibold mb-4">Create New Project</h2>
          <form onSubmit={handleCreateProject} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Project Name
              </label>
              <input
                type="text"
                value={newProject.name}
                onChange={(e) =>
                  setNewProject((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder="my-awesome-project"
                className="w-full px-4 py-2 rounded-md border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
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
                className="w-full px-4 py-2 rounded-md border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
              >
                Create Project
              </button>
              <button
                type="button"
                onClick={() => setIsCreating(false)}
                className="px-4 py-2 rounded-md border border-border hover:bg-accent"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {projects.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Github className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No projects yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {projects.map((project) => (
            <div
              key={project.id}
              className="p-4 rounded-lg border border-border bg-card flex justify-between items-center"
            >
              <div>
                <h3 className="font-semibold">{project.name}</h3>
                {project.description && (
                  <p className="text-sm text-muted-foreground">
                    {project.description}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {project.github_repo && (
                  <a
                    href={`https://github.com/${project.github_repo}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 rounded-md hover:bg-accent"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                )}
                <span
                  className={`px-2 py-1 text-xs rounded-full ${
                    project.status === "active"
                      ? "bg-green-500/10 text-green-500"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {project.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
