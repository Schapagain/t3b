import { useState, useEffect, useRef } from "react";
import "./index.css";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { MessageBubble } from "@/components/message-bubble";
import { ChatInput } from "@/components/chat-input";
import { useSync } from "./hooks/useSync";

export default function App() {
  const { sync, syncing, syncResult } = useSync();
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([
    {
      text: "Test 1",
      role: "user",
    },
    {
      text: "Test 2",
      role: "assistant",
    },
    {
      text: "Test 3",
      role: "user",
    },
    {
      text: "Test 4",
      role: "assistant",
    },
    {
      text: "Testing a long long long paragraph. And yet another sentence that is somewhat long.",
      role: "user",
    },
  ]);
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    if (!message.trim()) return;
    setMessages((messages) =>
      messages.concat({
        text: message,
      }),
    );
    setLoading(true);
    setResponse(null);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: "demo", message }),
      });
      const data = await res.json();
      setResponse(data.answer);
    } catch {
      setResponse("Error reaching backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen min-w-screen bg-slate-700 text-2xl">
      <div className="max-w-4xl w-full py-4 mx-auto">
        <div className="flex gap-2 mb-8 items-center justify-between">
          <h1 className="text-2xl text-gray-50">T3B — Talk to the Board</h1>
          <Button variant="outline" size="sm" onClick={sync} disabled={syncing}>
            <RefreshCw className={syncing ? "animate-spin" : ""} />
            {syncing ? "Syncing..." : "Sync Trello"}
          </Button>
        </div>

        <ScrollArea className="h-[60vh] my-4 mt-22 pr-8">
          <div className="flex flex-col gap-4">
            {messages.map((msg, idx) => (
              <MessageBubble key={idx} msg={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>

        <div className="flex gap-4 items-end">
          <ChatInput
            rows={1}
            className="resize-none overflow-hidden min-h-0 text-gray-50"
            placeholder="Ask something..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
          />
          <Button size="lg" onClick={handleSend} disabled={loading}>
            {loading ? "..." : "Send"}
          </Button>
        </div>
      </div>
    </div>
  );
}
