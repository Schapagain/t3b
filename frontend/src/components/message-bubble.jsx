import { cn } from "@/lib/utils";

function MessageBubble({ msg }) {
  const userMsgClasses = "ml-auto";
  const agentMsgClasses = "mr-auto";

  const leftBubble = msg.role === "assistant";

  return (
    <div
      className={cn(
        "flex flex-col items-start",
        leftBubble ? agentMsgClasses : userMsgClasses,
      )}
    >
      <div className="flex flex-col w-full min-w-sm max-w-lg leading-1.5 p-4 bg-[#F9FAFB] rounded-sm">
        <p className="text-sm text-body">{msg.text}</p>
      </div>
      <span
        className={cn(
          "text-xs text-body mt-0.5 text-gray-300",
          leftBubble ? "mr-auto" : "ml-auto",
        )}
      >
        {leftBubble ? "Received at: " : "Sent at: "} 11:46
      </span>
    </div>
  );
}

export { MessageBubble };
