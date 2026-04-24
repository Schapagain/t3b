import { useState } from "react";

export function useSync() {
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState(null);

  async function sync() {
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await fetch("/api/ingest/sync", { method: "POST" });
      const data = await res.json();
      setSyncResult({ ok: true, cardsIngested: data.cards_ingested });
    } catch {
      setSyncResult({ ok: false });
    } finally {
      setSyncing(false);
    }
  }

  return { sync, syncing, syncResult };
}
