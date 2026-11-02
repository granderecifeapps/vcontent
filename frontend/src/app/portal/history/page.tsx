"use client";

import { Stack, Text } from "@mantine/core";
import Link from "next/link";
import { useEffect, useState } from "react";
import { LoadBox, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { fail } from "@/lib/feedback";
import { ACTIONS, formatWhen } from "@/lib/labels";
import type { HistoryEvent, Page } from "@/lib/types";

export default function HistoryPage() {
  const [page, setPage] = useState<Page<HistoryEvent> | null>(null);
  useEffect(() => {
    void api<Page<HistoryEvent>>("/api/history?page_size=50").then(setPage).catch(fail);
  }, []);
  if (!page) return <LoadBox />;
  return (
    <>
      <PageHeader kicker="Registro" title="Histórico" />
      <Stack>
        {page.items.map((item) => (
          <Link key={item.id} href={`/portal/contents/${item.content_id}`} className="timeline-card">
            <Text fw={600}>{item.content_title}</Text>
            <Text size="sm">
              {ACTIONS[item.action] ?? item.action} · {item.actor_name}
            </Text>
            <Text size="xs" c="dimmed">
              {formatWhen(item.created_at)}
            </Text>
            {item.reason ? <Text size="sm">{item.reason}</Text> : null}
          </Link>
        ))}
        {!page.items.length ? <Text c="dimmed">Nenhuma ação ainda.</Text> : null}
      </Stack>
    </>
  );
}
