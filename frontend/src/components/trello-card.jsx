import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "./ui/badge";

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
        <p className="mt-3">
          Assigned to: <span className="capitalize">{assignee || "N/A"}</span>
        </p>
      </CardContent>
      <CardFooter>
        {link && (
          <a target="_blank" href={link} rel="noopener noreferrer">
            See in Trello
          </a>
        )}
      </CardFooter>
    </Card>
  );
}

export { TrelloCard };
