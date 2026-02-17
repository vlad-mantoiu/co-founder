"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { MessageCircle, X } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { ChatMessage, type Message } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

interface FloatingChatProps {
  projectId?: string;
}

interface ProjectContext {
  project_id: string;
  stage: number;
  status: string;
  build_status?: string;
}

let messageCounter = 0;
function nextId() {
  return `msg-${++messageCounter}`;
}

function parseActions(
  content: string,
): { text: string; actions: { type: string; payload: string }[] } {
  const actions: { type: string; payload: string }[] = [];
  const text = content.replace(
    /\[ACTION:(navigate|start_build):([^\]]+)\]/g,
    (_match, type, payload) => {
      actions.push({ type, payload });
      return "";
    },
  );
  return { text: text.trim(), actions };
}

export function FloatingChat({ projectId }: FloatingChatProps) {
  const { getToken } = useAuth();
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isResponding, setIsResponding] = useState(false);
  const [projectContext, setProjectContext] = useState<ProjectContext | null>(
    null,
  );
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch project context once when panel opens (if projectId provided)
  useEffect(() => {
    if (!isOpen || !projectId || projectContext) return;

    async function fetchContext() {
      try {
        const res = await apiFetch(
          `/api/projects/${projectId}`,
          getToken,
          {},
        );
        if (res.ok) {
          const data = await res.json();
          setProjectContext({
            project_id: projectId as string,
            stage: data.stage_number ?? 0,
            status: data.status ?? "unknown",
            build_status: data.build_status,
          });
        }
      } catch {
        // Non-fatal — proceed without context
      }
    }

    fetchContext();
  }, [isOpen, projectId, projectContext, getToken]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(
    async (text: string) => {
      const userMessage: Message = {
        id: nextId(),
        role: "user",
        content: text,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsResponding(true);

      try {
        const res = await apiFetch("/api/agent/chat", getToken, {
          method: "POST",
          body: JSON.stringify({
            message: text,
            project_context: projectContext,
          }),
        });

        if (!res.ok) {
          throw new Error(`API error: ${res.status}`);
        }

        const data = await res.json();
        const rawContent: string = data.response ?? data.message ?? "";
        const { text: cleanText, actions } = parseActions(rawContent);

        const assistantMessage: Message = {
          id: nextId(),
          role: "assistant",
          content: cleanText || "I'm here to help. What would you like to know?",
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, assistantMessage]);

        // Execute parsed actions
        for (const action of actions) {
          if (action.type === "navigate") {
            router.push(action.payload);
          } else if (action.type === "start_build" && action.payload) {
            try {
              await apiFetch(
                `/api/generation/start/${action.payload}`,
                getToken,
                { method: "POST" },
              );
            } catch {
              // Non-fatal
            }
          }
        }
      } catch (err) {
        const errorMessage: Message = {
          id: nextId(),
          role: "assistant",
          content: "Sorry, something went wrong. Please try again.",
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, errorMessage]);
        console.error("Chat error:", err);
      } finally {
        setIsResponding(false);
      }
    },
    [getToken, projectContext, router],
  );

  function handleOpen() {
    setIsOpen(true);
  }

  function handleClose() {
    setIsOpen(false);
    // Conversations are ephemeral — clear on close per locked decision
    setMessages([]);
    setIsResponding(false);
  }

  return (
    <>
      {/* Floating bubble button */}
      <button
        onClick={isOpen ? handleClose : handleOpen}
        className={cn(
          "fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-lg",
          "flex items-center justify-center transition-all duration-200",
          isOpen
            ? "bg-white/10 border border-white/20 text-white"
            : "bg-brand hover:bg-brand/80 text-white shadow-glow",
        )}
        aria-label={isOpen ? "Close chat" : "Open Co-Founder chat"}
      >
        <AnimatePresence mode="wait" initial={false}>
          {isOpen ? (
            <motion.span
              key="close"
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <X className="w-5 h-5" />
            </motion.span>
          ) : (
            <motion.span
              key="open"
              initial={{ rotate: 90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: -90, opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <MessageCircle className="w-5 h-5" />
            </motion.span>
          )}
        </AnimatePresence>
      </button>

      {/* Chat panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className={cn(
              "fixed bottom-24 right-6 z-50",
              "w-96 h-[500px] glass-strong rounded-2xl border border-white/10",
              "flex flex-col overflow-hidden shadow-2xl",
            )}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 flex-shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-brand/20 border border-brand/30 flex items-center justify-center">
                  <MessageCircle className="w-3.5 h-3.5 text-brand" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">
                    Co-Founder Chat
                  </p>
                  {projectContext && (
                    <p className="text-xs text-white/40">
                      Project context loaded
                    </p>
                  )}
                </div>
              </div>
              <button
                onClick={handleClose}
                className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto scrollbar-thin px-3 py-3 flex flex-col gap-3">
              {messages.length === 0 && (
                <div className="flex-1 flex flex-col items-center justify-center text-center px-4">
                  <div className="w-10 h-10 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center mb-3">
                    <MessageCircle className="w-5 h-5 text-brand/60" />
                  </div>
                  <p className="text-sm text-white/60 font-medium">
                    Ask me anything
                  </p>
                  <p className="text-xs text-white/30 mt-1">
                    I can answer questions and help you navigate your project.
                  </p>
                </div>
              )}
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              {isResponding && (
                <div className="self-start flex items-center gap-1.5 px-3 py-2 bg-white/10 rounded-2xl rounded-bl-sm border border-white/10">
                  <span className="w-1.5 h-1.5 rounded-full bg-white/50 animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-white/50 animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-white/50 animate-bounce [animation-delay:300ms]" />
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <ChatInput
              onSend={sendMessage}
              disabled={isResponding}
              placeholder="Ask your co-founder..."
            />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
