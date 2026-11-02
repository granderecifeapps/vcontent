"use client";

import { Card, Group, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { fail } from "@/lib/feedback";
import { scheduleLabel } from "@/lib/labels";
import type { Content, Page } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";
import { EmptyState, LoadBox } from "./ui";

export function ContentCollection({
  status,
  hrefBase,
  empty,
  clientId,
  query = "",
  audience = "admin",
}: {
  status?: string;
  hrefBase: string;
  empty: string;
  clientId?: string;
  query?: string;
  audience?: "admin" | "client";
}) {
  const [page, setPage] = useState<Page<Content> | null>(null);
  useEffect(() => {
    const params = new URLSearchParams(query);
    params.set("page_size", "24");
    if (status) params.set("status", status);
    if (clientId) params.set("client_id", clientId);
    void api<Page<Content>>(`/api/contents?${params.toString()}`)
      .then(setPage)
      .catch(fail);
  }, [status, clientId, query]);
  if (!page) return <LoadBox />;
  if (!page.items.length) return <EmptyState title="Nada por aqui" text={empty} />;
  return (
    <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
      {page.items.map((item) => (
        <Card key={item.id} component={Link} href={`${hrefBase}/${item.id}`}>
          {item.media[0]?.url ? (
            item.media[0].mime_type.startsWith("video/") ? (
              <video src={item.media[0].url} style={{ width: "100%", height: 180, objectFit: "cover", borderRadius: 14, background: "#111" }} />
            ) : (
              <img src={item.media[0].url} alt="" style={{ width: "100%", height: 180, objectFit: "cover", borderRadius: 14 }} />
            )
          ) : null}
          <Stack gap={6} mt="sm">
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                {item.platform.name} · {item.format.name}
              </Text>
              <StatusBadge status={item.status} audience={audience} />
            </Group>
            <Title order={4}>{item.title}</Title>
            <Text size="sm">{item.client_name}</Text>
            <Text size="sm" c="dimmed">
              {scheduleLabel(item.scheduled_date, item.scheduled_time)}
            </Text>
            {item.status === "in_progress" && item.waiting_note ? <Text size="sm">{item.waiting_note}</Text> : null}
            {item.latest_reason && item.status !== "in_progress" ? <Text size="sm">Ajuste: {item.latest_reason}</Text> : null}
          </Stack>
        </Card>
      ))}
    </SimpleGrid>
  );
}
