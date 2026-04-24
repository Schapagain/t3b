import { cn } from "@/lib/utils";
import { TrelloCard } from "./trello-card";

function MessageBubble({ msg }) {
  const userMsgClasses = "ml-auto";
  const agentMsgClasses = "mr-auto";

  const leftBubble = msg.role === "assistant";
  console.log("got cards:", msg);
  return (
    <div
      className={cn(
        "flex flex-col items-start",
        leftBubble ? agentMsgClasses : userMsgClasses,
      )}
    >
      <div className="flex flex-col w-full min-w-sm max-w-lg leading-1.5 p-4 bg-[#F9FAFB] rounded-xs">
        <p className="text-sm text-body">{msg.text}</p>
        {msg.tools_used && msg.tools_used.length > 0 && (
          <p className="text-gray-600 text-sm mt-2 flex flex-wrap gap-2">
            Tools used:{" "}
            {msg.tools_used.map((tool, idx) => (
              <span
                key={tool + idx}
                className="bg-slate-500 text-white px-2 rounded-xs"
              >
                {tool}
              </span>
            ))}
          </p>
        )}
      </div>
      {msg.cards && msg.cards.length > 0 && (
        <div className="flex flex-wrap gap-2 my-2">
          {msg.cards.map((card) => (
            <TrelloCard
              key={card.id}
              title={card.name}
              description={card.desc}
              link={card.url}
              {...card}
            />
          ))}
        </div>
      )}
      <span
        className={cn(
          "text-xs text-body mt-0.5 text-gray-300",
          leftBubble ? "mr-auto" : "ml-auto",
        )}
      >
        {leftBubble ? "Received at: " : "Sent at: "}{" "}
        {new Date(msg.timestamp).toLocaleTimeString()}
      </span>
    </div>
  );
}

export { MessageBubble };
