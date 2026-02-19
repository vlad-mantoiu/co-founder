"use client";

import { useSearchParams } from "next/navigation";
import { ChatWindow } from "@/components/chat/ChatWindow";

export default function ChatPage() {
  const searchParams = useSearchParams();
  const demoMode = searchParams.get("demo") === "true";

  return <ChatWindow demoMode={demoMode} />;
}
