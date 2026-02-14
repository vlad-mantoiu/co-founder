"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { Send, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  node?: string;
  timestamp: Date;
}

export default function ChatPage() {
  const { getToken } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setStatus("Connecting to co-founder...");

    try {
      const response = await apiFetch("/api/agent/chat/stream", getToken, {
        method: "POST",
        body: JSON.stringify({
          message: userMessage.content,
          project_id: "default",
          session_id: sessionId,
        }),
      });

      if (!response.ok) throw new Error("Failed to connect");

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No reader available");

      let assistantContent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              setSessionId(data.session_id);
              setStatus(`${data.node}: ${data.message}`);

              if (data.node === "complete" || data.node === "error") {
                assistantContent = data.message;
              }
            } catch {
              // Ignore parse errors
            }
          }
        }
      }

      if (assistantContent) {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            role: "assistant",
            content: assistantContent,
            timestamp: new Date(),
          },
        ]);
      }
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "assistant",
          content: "Sorry, I encountered an error. Please try again.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
      setStatus(null);
    }
  };

  return (
    <div className="h-[calc(100vh-7rem)] flex flex-col glass-strong rounded-2xl overflow-hidden">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-16">
            <h2 className="font-display text-xl font-semibold text-white mb-2">
              Chat with your co-founder
            </h2>
            <p className="text-muted-foreground mb-8 max-w-md mx-auto">
              Describe what you want to build, and I&apos;ll help you plan,
              code, and ship it.
            </p>
            <div className="grid gap-2 max-w-md mx-auto">
              <SuggestionButton
                onClick={() =>
                  setInput("Create a REST API for user authentication")
                }
              >
                Create a REST API for user authentication
              </SuggestionButton>
              <SuggestionButton
                onClick={() =>
                  setInput("Add a dark mode toggle to the settings page")
                }
              >
                Add a dark mode toggle to the settings page
              </SuggestionButton>
              <SuggestionButton
                onClick={() => setInput("Fix the bug in the checkout flow")}
              >
                Fix the bug in the checkout flow
              </SuggestionButton>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                message.role === "user"
                  ? "bg-brand text-white"
                  : "glass border border-white/5"
              }`}
            >
              <p className="whitespace-pre-wrap text-sm">{message.content}</p>
              {message.node && (
                <p className="text-xs opacity-50 mt-1.5">{message.node}</p>
              )}
            </div>
          </div>
        ))}

        {isLoading && status && (
          <div className="flex items-center gap-2.5 text-neon-cyan">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">{status}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-white/5 p-4 flex gap-3"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe what you want to build..."
          className="flex-1 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand/50 focus:border-transparent transition-all"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="px-4 py-2.5 rounded-xl bg-brand text-white hover:bg-brand-dark disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </form>
    </div>
  );
}

function SuggestionButton({
  children,
  onClick,
}: {
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="text-left px-4 py-2.5 text-sm rounded-xl border border-white/10 text-muted-foreground hover:text-white hover:bg-white/5 hover:border-white/20 transition-all"
    >
      {children}
    </button>
  );
}
