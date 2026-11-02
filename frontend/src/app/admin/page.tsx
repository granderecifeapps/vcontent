"use client";

import { Card, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import Link from "next/link";
import { useEffect, useState } from "react";
import { PageHeader, StatCard, LoadBox } from "@/components/ui";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { fail } from "@/lib/feedback";
import { formatWhen } from "@/lib/labels";
import type { Content } from "@/lib/types";

type Event = {
  id: string;
  content_id: string;
  content_title: string;
  client_name: string | null;
  actor_name: string;
  reason: string | null;
  created_at: string;
};

type Dashboard = {
  active_clients: number;
  total_contents: number;
  pending: number;
  approved: number;
  changes_requested: number;
  scheduled: number;
  published: number;
  in_progress: number;
  recent_contents: Content[];
  recent_approvals: Event[];
  recent_changes: Event[];
  clients_with_pending: { id: string; company_name: string; pending: number }[];
};

export default function AdminHome() {
  const [data, setData] = useState<Dashboard | null>(null);
  useEffect(() => {
    void api<Dashboard>("/api/dashboard").then(setData).catch(fail);
  }, []);
  if (!data) return <LoadBox />;
  return (
    <Stack>
      <PageHeader kicker="Operação" title="Dashboard" description="O que está ativo, o que espera aprovação e o que voltou para ajuste." />
      <SimpleGrid cols={{ base: 2, md: 4 }}>
        <StatCard label="Clientes ativos" value={data.active_clients} />
        <StatCard label="Conteúdos" value={data.total_contents} />
        <StatCard label="Aguardando" value={data.pending} />
        <StatCard label="Aprovados" value={data.approved} />
        <StatCard label="Ajustes" value={data.changes_requested} />
        <StatCard label="Programados" value={data.scheduled} />
        <StatCard label="Publicados" value={data.published} />
        <StatCard label="Em andamento" value={data.in_progress} />
      </SimpleGrid>
      <SimpleGrid cols={{ base: 1, md: 2 }} mt="md">
        <Card>
          <Title order={4}>Últimos conteúdos</Title>
          <Stack mt="sm" gap="sm">
            {data.recent_contents.map((item) => (
              <Link key={item.id} href={`/admin/contents/${item.id}`}>
                <Text fw={600}>{item.title}</Text>
                <Text size="sm" c="dimmed">
                  {item.client_name}
                </Text>
                <StatusBadge status={item.status} />
              </Link>
            ))}
          </Stack>
        </Card>
        <Card>
          <Title order={4}>Clientes com pendência</Title>
          <Stack mt="sm">
            {data.clients_with_pending.length ? (
              data.clients_with_pending.map((item) => (
                <Link key={item.id} href={`/admin/clients/${item.id}`}>
                  <Text fw={600}>{item.company_name}</Text>
                  <Text size="sm" c="dimmed">
                    {item.pending} aguardando
                  </Text>
                </Link>
              ))
            ) : (
              <Text c="dimmed">Nenhum cliente com fila aberta.</Text>
            )}
          </Stack>
        </Card>
        <Card>
          <Title order={4}>Últimas aprovações</Title>
          <EventList items={data.recent_approvals} />
        </Card>
        <Card>
          <Title order={4}>Últimos pedidos de ajuste</Title>
          <EventList items={data.recent_changes} />
        </Card>
      </SimpleGrid>
    </Stack>
  );
}

function EventList({ items }: { items: Event[] }) {
  if (!items.length) return <Text c="dimmed" mt="sm">Nada registrado ainda.</Text>;
  return (
    <Stack mt="sm" gap="sm">
      {items.map((item) => (
        <Link key={item.id} href={`/admin/contents/${item.content_id}`}>
          <Text fw={600}>{item.content_title}</Text>
          <Text size="sm" c="dimmed">
            {item.actor_name} · {formatWhen(item.created_at)}
          </Text>
          {item.reason ? <Text size="sm">{item.reason}</Text> : null}
        </Link>
      ))}
    </Stack>
  );
}
