"use client";

import { Button, Group, Stack, Tabs, Text, Title } from "@mantine/core";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { CalendarBoard } from "@/components/CalendarBoard";
import { ContractManager } from "@/components/ContractManager";
import { ContentCollection } from "@/components/ContentCollection";
import { LoadBox, StatCard } from "@/components/ui";
import { api } from "@/lib/api";
import { fail, ok } from "@/lib/feedback";
import { statusLabel } from "@/lib/labels";
import type { Client, HistoryEvent, Page } from "@/lib/types";

export default function ClientPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [client, setClient] = useState<Client | null>(null);
  const [history, setHistory] = useState<HistoryEvent[]>([]);

  useEffect(() => {
    void Promise.all([api<Client>(`/api/clients/${params.id}`), api<Page<HistoryEvent>>(`/api/history?client_id=${params.id}&page_size=30`)])
      .then(([detail, events]) => {
        setClient(detail);
        setHistory(events.items);
      })
      .catch(fail);
  }, [params.id]);

  if (!client) return <LoadBox />;
  return (
    <Stack>
      <Group justify="space-between" align="flex-end">
        <div>
          <p className="kicker">Cliente</p>
          <Title order={2}>{client.company_name}</Title>
          <Text c="dimmed">
            {client.contact_name} · {client.email}
          </Text>
        </div>
        <Group>
          <Button variant="default" onClick={() => router.push(`/admin/clients/${client.id}/edit`)}>
            Editar
          </Button>
          <Button
            color="red"
            variant="light"
            onClick={() => {
              if (!window.confirm("Desativar e ocultar este cliente? Os conteúdos e o histórico permanecem.")) return;
              void api(`/api/clients/${client.id}`, { method: "DELETE" })
                .then(() => {
                  ok("Cliente removido da operação.");
                  router.push("/admin/clients");
                })
                .catch(fail);
            }}
          >
            Excluir
          </Button>
        </Group>
      </Group>
      <Tabs defaultValue="overview" mt="md">
        <Tabs.List>
          <Tabs.Tab value="overview">Visão geral</Tabs.Tab>
          <Tabs.Tab value="contents">Conteúdos</Tabs.Tab>
          <Tabs.Tab value="calendar">Calendário</Tabs.Tab>
          <Tabs.Tab value="approvals">Aprovações</Tabs.Tab>
          <Tabs.Tab value="history">Histórico</Tabs.Tab>
          <Tabs.Tab value="contract">Contrato</Tabs.Tab>
          <Tabs.Tab value="info">Cadastro</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="overview" pt="md">
          <Group grow align="stretch">
            {Object.entries(client.stats ?? {}).map(([status, count]) => (
              <StatCard key={status} label={statusLabel(status)} value={count} />
            ))}
          </Group>
          <Text mt="md">{client.description || "Sem descrição."}</Text>
        </Tabs.Panel>
        <Tabs.Panel value="contents" pt="md">
          <ContentCollection hrefBase="/admin/contents" clientId={client.id} empty="Este cliente ainda não tem conteúdos." />
        </Tabs.Panel>
        <Tabs.Panel value="calendar" pt="md">
          <CalendarBoard baseHref="/admin/contents" lockedClientId={client.id} />
        </Tabs.Panel>
        <Tabs.Panel value="approvals" pt="md">
          <ContentCollection
            hrefBase="/admin/contents"
            clientId={client.id}
            status="pending_approval,resubmitted,changes_requested,in_review,approved"
            empty="Nenhuma aprovação em andamento."
          />
        </Tabs.Panel>
        <Tabs.Panel value="history" pt="md">
          <Stack>
            {history.map((item) => (
              <Text key={item.id}>
                {item.content_title} · {item.action} · {item.actor_name}
                {item.reason ? ` — ${item.reason}` : ""}
              </Text>
            ))}
          </Stack>
        </Tabs.Panel>
        <Tabs.Panel value="contract" pt="md">
          <ContractManager client={client} onChange={setClient} />
        </Tabs.Panel>
        <Tabs.Panel value="info" pt="md">
          <Stack gap={4}>
            <Text>Telefone: {client.phone || "—"}</Text>
            <Text>Status: {client.status === "active" ? "Ativo" : "Inativo"}</Text>
            <Text>Login: {client.access?.email}</Text>
            <Text>Observações: {client.internal_notes || "—"}</Text>
          </Stack>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
