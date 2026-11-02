"use client";

import { Button, Group, Stack, Text } from "@mantine/core";
import Link from "next/link";
import { useEffect, useState } from "react";
import { LoadBox, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { fail, ok } from "@/lib/feedback";
import { formatWhen } from "@/lib/labels";
import type { Notice, Page } from "@/lib/types";

export default function NotificationsPage() {
  const [page, setPage] = useState<Page<Notice> & { unread_count: number } | null>(null);

  function load() {
    return api<Page<Notice> & { unread_count: number }>("/api/notifications?page_size=50").then(setPage);
  }

  useEffect(() => {
    void load().catch(fail);
  }, []);

  if (!page) return <LoadBox />;
  return (
    <>
      <PageHeader
        kicker="Avisos"
        title="Notificações"
        description="Aprovações, ajustes e reenvios ficam registrados aqui. E-mail e WhatsApp entram depois, no mesmo registro."
        action={
          <Button
            variant="default"
            onClick={() =>
              void api("/api/notifications/read-all", { method: "POST" })
                .then(() => {
                  ok("Tudo marcado como lido.");
                  return load();
                })
                .catch(fail)
            }
          >
            Marcar como lidas
          </Button>
        }
      />
      <Stack>
        {page.items.map((item) => (
          <Group key={item.id} justify="space-between" align="flex-start" p="md" style={{ background: item.read_at ? "#fff" : "#f8efea", border: "1px solid #e7ddd2", borderRadius: 16 }}>
            <div>
              <Text fw={600}>{item.title}</Text>
              <Text size="sm">{item.body}</Text>
              <Text size="xs" c="dimmed">
                {formatWhen(item.created_at)}
              </Text>
            </div>
            {item.data?.content_id ? (
              <Button
                component={Link}
                href={`/admin/contents/${item.data.content_id}`}
                variant="subtle"
                onClick={() => void api(`/api/notifications/${item.id}/read`, { method: "POST" })}
              >
                Abrir
              </Button>
            ) : null}
          </Group>
        ))}
        {!page.items.length ? <Text c="dimmed">Nenhuma notificação ainda.</Text> : null}
      </Stack>
    </>
  );
}
