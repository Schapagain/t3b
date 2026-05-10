import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function getCardChanges(card, args) {
  const changes = [];

  if (args.status != null && args.status !== card.status) {
    changes.push({ field: "status", from: card.status, to: args.status });
  }

  if (args.assignee != null && args.assignee !== card.assignee) {
    changes.push({ field: "assignee", from: card.assignee, to: args.assignee });
  }

  if (args.due != null) {
    const currentDue = card.due
      ? new Date(Number.isInteger(card.due) ? card.due * 1000 : card.due)
      : null;
    const proposedDue = new Date(
      Number.isInteger(args.due) ? args.due * 1000 : args.due,
    );
    const currentDateStr = currentDue?.toISOString().slice(0, 10);
    const proposedDateStr = proposedDue.toISOString().slice(0, 10);
    if (!currentDue || currentDateStr !== proposedDateStr) {
      changes.push({
        field: "due",
        from: currentDateStr,
        to: proposedDateStr,
      });
    }
  }

  return changes;
}
