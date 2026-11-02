"use client";

import { useEffect, useState } from "react";
import { SwipeDeck } from "@/components/SwipeDeck";
import { api } from "@/lib/api";
import { fail, ok } from "@/lib/feedback";
import type { Content } from "@/lib/types";

export default function ApprovePage() {
  const [items, setItems] = useState<Content[] | null>(null);
  useEffect(() => {
    void api<Content[]>("/api/approvals/queue").then(setItems).catch(fail);
  }, []);
  if (!items) return null;
  return (
    <div style={{ paddingBottom: 88 }}>
      <SwipeDeck
        items={items}
        onApprove={async (item) => {
          await api(`/api/approvals/${item.id}/approve`, { method: "POST" });
          setItems((current) => (current ?? []).filter((entry) => entry.id !== item.id));
          ok("Conteúdo aprovado.");
        }}
        onChanges={async (item, reason) => {
          try {
            await api(`/api/approvals/${item.id}/changes`, { method: "POST", body: JSON.stringify({ reason }) });
            setItems((current) => (current ?? []).filter((entry) => entry.id !== item.id));
            ok("Ajuste enviado.");
          } catch (error) {
            fail(error);
            throw error;
          }
        }}
      />
    </div>
  );
}
