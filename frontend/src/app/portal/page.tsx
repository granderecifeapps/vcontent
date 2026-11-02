"use client";

import { Button, Card, Stack, Text, Title } from "@mantine/core";
import Link from "next/link";
import { useEffect, useState } from "react";
import { LoadBox, PageHeader, StatCard } from "@/components/ui";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fail } from "@/lib/feedback";
import { scheduleLabel } from "@/lib/labels";
import type { Content } from "@/lib/types";

type Dashboard = { pending: number; approved: number; changes_requested: number; in_progress: number; upcoming: Content[] };

export default function PortalHome() {
  const { user } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  useEffect(() => {
    void api<Dashboard>("/api/dashboard").then(setData).catch(fail);
  }, []);
  if (!data) return <LoadBox />;
  return (
    <Stack>
      <PageHeader
        kicker={user?.client?.company_name || "Portal"}
        title="Olá"
        description="Aprove o que está pronto e acompanhe o que já entrou no calendário."
        action={
          <Button component={Link} href="/portal/approve">
            Aprovar agora
          </Button>
        }
      />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        <StatCard label="Aguardando você" value={data.pending} />
        <StatCard label="Aprovados" value={data.approved} />
        <StatCard label="Em ajuste" value={data.changes_requested} />
        <StatCard label="Em andamento" value={data.in_progress} />
      </div>
      <Card>
        <Title order={4}>Próximas publicações</Title>
        <Stack mt="sm">
          {data.upcoming.length ? (
            data.upcoming.map((item) => (
              <Link key={item.id} href={`/portal/contents/${item.id}`}>
                <Text fw={600}>{item.title}</Text>
                <Text size="sm" c="dimmed">
                  {item.platform.name} · {scheduleLabel(item.scheduled_date, item.scheduled_time)}
                </Text>
                <StatusBadge status={item.status} audience="client" />
              </Link>
            ))
          ) : (
            <Text c="dimmed">Nenhuma publicação programada.</Text>
          )}
        </Stack>
      </Card>
    </Stack>
  );
}
