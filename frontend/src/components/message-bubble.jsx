import { cn, getCardChanges } from "@/lib/utils";
import { TrelloCard } from "./trello-card";
import { Check, CheckCheck, CircleX, X } from "lucide-react";
import { Spinner } from "./ui/spinner";
import { useEffect, useState } from "react";

function getToolText(status, toolName) {
  return status === "approval_required"
    ? `Attempting to run tool ${toolName}`
    : status === "started"
      ? `Using tool ${toolName}`
      : status === "finished"
        ? `Tool ${toolName} ran successfully`
        : `${toolName} run failed`;
}

function ToolBubble({
  tool,
  onToolApprove = () => null,
  onToolReject = () => null,
}) {
  const started = tool["status"] === "started";
  const finished = tool["status"] === "finished";
  const failed = tool["status"] === "failed";
  const approvalRequired = tool["status"] === "approval_required";
  const card = tool["card"];
  const approvalStatus = tool["approvalStatus"];

  const handleApprovalAction = (type) => {
    if (type === "approved") {
      onToolApprove(tool["name"]);
    } else {
      onToolReject(tool["name"]);
    }
  };

  const approvalButtonClasses = cn(
    "flex gap-2 items-center bg-[#F9FAFB] text-gray-900 p-2",
    "rounded-sm mt-2 w-32 justify-center mb-4 transition-colors",
    approvalStatus === "pending" ? "hover:text-[#F9FAFB] cursor-pointer" : "",
  );

  let cardChanges = [];
  if ((approvalRequired || approvalStatus) && card) {
    cardChanges = getCardChanges(card, tool["args"]);
  }

  return (
    <>
      <div className="flex flex-col mr-auto gap-2">
        <div className="flex items-center text-[#F9FAFB] text-[16px] gap-2">
          {getToolText(tool["status"], tool.name)}
          <div className="relative w-4 h-4">
            <Spinner
              className={cn(
                "absolute left-0 top-0 transition-opacity duration-300",
                started || approvalRequired ? "opacity-100" : "opacity-0",
              )}
            />
            <CheckCheck
              size={16}
              className={cn(
                "absolute left-0 top-0 transition-opacity duration-300",
                finished ? "opacity-100" : "opacity-0",
              )}
            />
            <CircleX
              size={16}
              className={cn(
                "text-red-400 absolute left-0 top-0 transition-opacity duration-300",
                failed ? "opacity-100" : "opacity-0",
              )}
            />
          </div>
        </div>
        {card && (
          <TrelloCard
            key={card.id}
            title={card.name}
            description={card.desc}
            link={card.url}
            {...card}
          />
        )}
      </div>
      <div className="flex flex-col ml-auto gap-2">
        {(approvalRequired || approvalStatus) && (
          <div className="flex flex-col text-[#F9FAFB] text-[16px]">
            <p className="mt-2">Make the following changes to this card?</p>
            {cardChanges.map((change) => (
              <p>
                {change.field}: {change.from} → {change.to}
              </p>
            ))}
            <div>
              <div className="flex gap-4">
                <button
                  className={cn(
                    approvalButtonClasses,
                    approvalStatus === "approved"
                      ? "bg-green-600 text-[#F9FAFB]"
                      : "",
                    approvalStatus == "pending" ? "hover:bg-green-600" : "",
                  )}
                  disabled={approvalStatus !== "pending"}
                  onClick={() => handleApprovalAction("approved")}
                >
                  Approve <Check />
                </button>
                <button
                  className={cn(
                    approvalButtonClasses,
                    approvalStatus === "rejected"
                      ? "bg-red-500 text-[#F9FAFB]"
                      : "",
                    approvalStatus == "pending" ? "hover:bg-red-500" : "",
                  )}
                  disabled={approvalStatus !== "pending"}
                  onClick={() => handleApprovalAction("rejected")}
                >
                  {" "}
                  Deny <X />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

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

export { MessageBubble, ToolBubble };
