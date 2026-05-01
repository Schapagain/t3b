import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "./ui/badge";
import { AlarmClock } from "lucide-react";

function StatusTag({ status }) {
  return <Badge className="text-xs">{status}</Badge>;
}

function TrelloCard({ title, description, link, status, due, assignee }) {
  return (
    <Card className="min-w-xs max-w-md">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <StatusTag status={status} />
      </CardHeader>
      <CardContent>
        <p>{description}</p>
      </CardContent>
      <CardFooter>
        <div className="flex w-full justify-between items-center">
          <p>
            Assigned to: <span className="capitalize">{assignee || "N/A"}</span>
            <span className="block flex items-center">
              <AlarmClock size={14} className="inline mr-1" />
              {
                <span className="capitalize">
                  {due
                    ? new Date(due * 1000).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })
                    : "N/A"}
                </span>
              }
            </span>
          </p>
          {link && (
            <a target="_blank" href={link} rel="noopener noreferrer">
              See in Trello
            </a>
          )}
        </div>
      </CardFooter>
    </Card>
  );
}

export { TrelloCard };
