import { useState, useEffect, useRef } from "react";
import "./index.css";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { MessageBubble } from "@/components/message-bubble";
import { ChatInput } from "@/components/chat-input";
import { useSync } from "./hooks/useSync";

const feOnlyMode = false;

const testCards = [
  {
    role: "user",
    text: "Can you get all cards in review please?",
    timestamp: 1777049629331,
  },
  {
    role: "assistant",
    text: 'I\'ve retrieved the cards that are currently "In Review." Here they are:\n\n1. **[Add social feed for following friends](https://trello.com/c/IN7NlTMN/5-add-social-feed-for-following-friends)**\n   - Assignee: Bob Demo\n   - Due: April 24, 2026\n\n2. **[Implement heart rate zone calculations](https://trello.com/c/ZMJshEpL/6-implement-heart-rate-zone-calculations)**\n   - Assignee: Alice Demo\n   - Due: April 25, 2026\n\n3. **[Write unit tests for workout logging API](https://trello.com/c/MolR0OxH/7-write-unit-tests-for-workout-logging-api)**\n   - Assignee: Dave Demo\n   - Due: April 24, 2026\n\nIf you need more details or further actions regarding these cards, please let me know!',
    tools_used: ["trello_sync", "search_cards"],
    cards: [
      {
        assignee: "Bob Demo",
        status: "In Review",
        name: "Add social feed for following friends",
        id: "69e98ce01e61b4017ad67f75",
        due: "2026-04-24T23:59:00.000Z",
        url: "https://trello.com/c/IN7NlTMN/5-add-social-feed-for-following-friends",
        desc: "",
      },
      {
        url: "https://trello.com/c/ZMJshEpL/6-implement-heart-rate-zone-calculations",
        due: "2026-04-25T23:59:00.000Z",
        id: "69e98ce144168ee5fcf70fad",
        name: "Implement heart rate zone calculations",
        assignee: "Alice Demo",
        status: "In Review",
        desc: "",
      },
      {
        assignee: "Dave Demo",
        due: "2026-04-24T23:59:00.000Z",
        url: "https://trello.com/c/MolR0OxH/7-write-unit-tests-for-workout-logging-api",
        name: "Write unit tests for workout logging API",
        id: "69e98ce2c58dac21682eddf6",
        status: "In Review",
        desc: "",
      },
    ],
    timestamp: 1777049637688,
  },
];

function EmptyChat() {
  return <div>Hello, how can I help?</div>;
}

export default function App() {
  const { sync, syncing, syncResult } = useSync();
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState(feOnlyMode ? testCards : []);
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
        role: "user",
        text: message,
        timestamp: Date.now(),
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

      setMessages((messages) =>
        messages.concat({
          role: "assistant",
          text: data["agent_response"],
          tools_used: data["tool_calls_used"],
          cards: data["cards"],
          timestamp: Date.now(),
        }),
      );
      setMessage("");
    } catch {
      setResponse("Error reaching backend.");
    } finally {
      setLoading(false);
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="min-h-screen min-w-screen bg-slate-700 text-4xl">
      <div className="max-w-5xl w-full py-4 mx-auto h-full">
        <div className="flex gap-2 mb-8 items-center justify-between">
          <h1 className="text-2xl text-gray-50">T3B — Talk to the Board</h1>
          <Button variant="outline" size="sm" onClick={sync} disabled={syncing}>
            <RefreshCw className={syncing ? "animate-spin" : ""} />
            {syncing ? "Syncing..." : "Sync Trello"}
          </Button>
        </div>

        <ScrollArea className="h-[75vh] my-4 mt-12 pr-8">
          {messages.length > 0 ? (
            <div className="flex flex-col gap-4">
              {messages.map((msg, idx) => (
                <MessageBubble key={idx} msg={msg} />
              ))}
              <div ref={bottomRef} />
            </div>
          ) : (
            <div className="flex items-center justify-center text-gray-50 pt-26">
              <EmptyChat />
            </div>
          )}
        </ScrollArea>

        <div className="flex gap-4 items-start h-12 relative">
          <ChatInput
            rows={1}
            className="resize-none overflow-hidden text-gray-50 min-h-0 w-4/5 h-full"
            placeholder="Ask something..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <Button
            className="h-full w-1/5"
            size="lg"
            onClick={handleSend}
            disabled={loading}
          >
            {loading ? "Thinking..." : "Send"}
          </Button>
        </div>
      </div>
    </div>
  );
}
