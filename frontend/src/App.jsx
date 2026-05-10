import { useState, useEffect, useRef } from "react";
import "./index.css";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { MessageBubble, ToolBubble } from "@/components/message-bubble";
import { ChatInput } from "@/components/chat-input";
import { useSync } from "./hooks/useSync";
import { Spinner } from "./components/ui/spinner";

const feOnlyMode = false;

const testCards = [
  {
    role: "user",
    text: "can you help me update the fix notification card that is currently in progress to done?",
    timestamp: 1778364664212,
  },
  {
    role: "tool",
    status: "finished",
    name: "search_cards",
  },
  {
    role: "tool",
    status: "approval_required",
    name: "update_card",
    args: {
      card_id: "69ebd05c661fa7094f39fc17",
      due: "2026-04-28T23:59:00.000Z",
      status: "Done",
      assignee: "dave demo",
    },
    card: {
      due: 1777420740,
      id: "69ebd05c661fa7094f39fc17",
      assignee_first_name: "dave",
      url: "https://trello.com/c/s45Bag73/32-fix-push-notification-delay-after-workout-ends",
      status: "In Progress",
      assignee_last_name: "demo",
      name: "Fix push notification delay after workout ends",
      desc: "Push notifications are firing 3-5 minutes late after workout completion. Suspected issue with background task queue on iOS. Needs investigation and fix.",
      assignee: "dave demo",
    },
  },
];

function EmptyChat() {
  return <div>Hello, how can I help?</div>;
}

export default function App() {
  const { sync, syncing, syncResult } = useSync();
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState(feOnlyMode ? testCards : []);

  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleToolRejection(tool_name) {
    handleSend(`Tool call rejected for ${tool_name}.`, "rejected", tool_name);
  }

  async function handleToolApproval(tool_name) {
    handleSend(`Tool call approved for ${tool_name}.`, "approved", tool_name);
  }

  async function handleSend(latestUserMessage, approvalStatus, toolName) {
    if (!latestUserMessage.trim()) return;
    setMessages((messages) => {
      let newMessages = [...messages];
      if (approvalStatus) {
        const toolRequiringApprovalIdx = messages.findLastIndex(
          (msg) =>
            msg.role == "tool" &&
            msg.status == "approval_required" &&
            msg.name == toolName,
        );
        newMessages = [
          ...newMessages.slice(0, toolRequiringApprovalIdx),
          {
            ...newMessages[toolRequiringApprovalIdx],
            approvalStatus: approvalStatus,
          },
          ...newMessages.slice(toolRequiringApprovalIdx + 1),
        ];
      }

      return newMessages.concat({
        role: "user",
        text: latestUserMessage,
        timestamp: Date.now(),
      });
    });
    setLoading(true);
    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: "demo",
          message: latestUserMessage,
          approved_tool: approvalStatus === "approved" ? toolName : undefined,
        }),
      });
      const streamReader = res.body.getReader();
      const streamDecoder = new TextDecoder();
      const dataPrefix = "data: ";
      while (true) {
        const { value, done } = await streamReader.read();
        if (done) break;
        const decoded = streamDecoder.decode(value);
        const decodedMessages = decoded
          .split("\n\n")
          .filter((msg) => msg.length > 0)
          .map((rawMsg) =>
            rawMsg.slice(rawMsg.indexOf(dataPrefix) + dataPrefix.length),
          )
          .map((rawMsg) => JSON.parse(rawMsg));

        setMessages((messages) => {
          const newMessages = [...messages];
          decodedMessages.forEach((msg) => {
            console.log("received new message::", msg);

            if (msg["agent_response"]) {
              (newMessages.push({
                role: "assistant",
                text: msg["agent_response"],
                tools_used: msg["tool_calls_used"],
                cards: msg["cards"],
                timestamp: Date.now(),
              }),
                setMessage(""));
            } else if (msg["tool_event"]) {
              const toolStatus = msg["tool_event"]["status"];
              if (toolStatus === "approval_required") {
                newMessages.push({
                  role: "tool",
                  status: toolStatus,
                  name: msg["tool_event"]["name"],
                  args: msg["tool_event"]["args"],
                  card: msg["tool_event"]["card"],
                  approvalStatus: "pending",
                });
              } else if (toolStatus === "started") {
                const lastToolApprovalRequiredIndex = newMessages.findLastIndex(
                  (m) =>
                    m.name === msg["tool_event"]["name"] &&
                    m.role === "tool" &&
                    m.status === "approval_required",
                );
                if (lastToolApprovalRequiredIndex >= 0) {
                  newMessages[lastToolApprovalRequiredIndex] = {
                    ...newMessages[lastToolApprovalRequiredIndex],
                    status: toolStatus,
                    approvalStatus: "approved",
                  };
                } else {
                  newMessages.push({
                    role: "tool",
                    status: toolStatus,
                    name: msg["tool_event"]["name"],
                  });
                }
              } else {
                const lastToolStartedIdx = newMessages.findLastIndex(
                  (msg) => msg.role === "tool" && msg.status === "started",
                );
                newMessages[lastToolStartedIdx] = {
                  ...newMessages[lastToolStartedIdx],
                  status: toolStatus,
                };
              }
            }
          });
          return newMessages;
        });
      }
    } catch (e) {
      console.error("Error:", e);
    } finally {
      setLoading(false);
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSend(message);
    }
  };
  console.log("messages::", messages);
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
              {messages.map((msg, idx) =>
                msg.role === "tool" ? (
                  <ToolBubble
                    key={idx}
                    tool={msg}
                    onToolApprove={handleToolApproval}
                    onToolReject={handleToolRejection}
                    loading={loading}
                  />
                ) : (
                  <MessageBubble key={idx} msg={msg} />
                ),
              )}
              {loading &&
                ((messages.slice(-1)[0].role === "tool" &&
                  messages.slice(-1)[0].status !== "started") ||
                  messages.slice(-1)[0].role === "user") && (
                  <div className="flex gap-2 text-[#F9FAFB] text-[16px]">
                    <Spinner />
                    Thinking...
                  </div>
                )}
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
            onClick={() => handleSend(message)}
            disabled={loading}
          >
            {loading ? "Thinking..." : "Send"}
          </Button>
        </div>
      </div>
    </div>
  );
}
