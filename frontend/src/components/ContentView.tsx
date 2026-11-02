"use client";

import { Button, Group, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { fail, ok } from "@/lib/feedback";
import { ACTIONS, formatWhen, scheduleLabel } from "@/lib/labels";
import type { Content, HistoryEvent } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

export function ContentView({ id, mode }: { id: string; mode: "admin" | "client" }) {
  const router = useRouter();
  const [content, setContent] = useState<Content | null>(null);
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [slide, setSlide] = useState(0);

  async function load() {
    const [item, events] = await Promise.all([
      api<Content>(`/api/contents/${id}`),
      api<HistoryEvent[]>(`/api/contents/${id}/history`),
    ]);
    setContent(item);
    setHistory(events);
  }

  useEffect(() => {
    void load().catch(fail);
  }, [id]);

  async function act(path: string, message: string) {
    try {
      await api(path, { method: "POST" });
      ok(message);
      await load();
    } catch (error) {
      fail(error);
    }
  }

  if (!content) return null;
  const media = content.media[slide] ?? content.media[0];
  const base = mode === "admin" ? "/admin" : "/portal";

  return (
    <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
      <Stack>
        <Group justify="space-between">
          <div>
            <Text c="dimmed" size="sm">
              {content.client_name} · {content.platform.name} · {content.format.name}
            </Text>
            <Title order={2}>{content.title}</Title>
          </div>
          <StatusBadge status={content.status} audience={mode} />
        </Group>
        <Text>{scheduleLabel(content.scheduled_date, content.scheduled_time)}</Text>
        {media?.url ? (
          media.mime_type.startsWith("video/") ? (
            <video src={media.url} controls playsInline style={{ width: "100%", borderRadius: 20, background: "#111", maxHeight: 520 }} />
          ) : (
            <img src={media.url} alt={content.title} style={{ width: "100%", borderRadius: 20, maxHeight: 520, objectFit: "cover" }} />
          )
        ) : (
          <Text c="dimmed">Nenhuma mídia anexada.</Text>
        )}
        {content.media.length > 1 ? (
          <Group>
            <Button variant="default" disabled={slide === 0} onClick={() => setSlide(slide - 1)}>
              Anterior
            </Button>
            <Text size="sm">
              {slide + 1} de {content.media.length}
            </Text>
            <Button variant="default" disabled={slide >= content.media.length - 1} onClick={() => setSlide(slide + 1)}>
              Próxima
            </Button>
          </Group>
        ) : null}
        {content.caption ? <Text style={{ whiteSpace: "pre-wrap" }}>{content.caption}</Text> : null}
        {content.copy_text ? <Text c="dimmed" style={{ whiteSpace: "pre-wrap" }}>{content.copy_text}</Text> : null}
        {content.hashtags ? <Text c="brand">{content.hashtags}</Text> : null}
        {content.status === "in_progress" && content.waiting_note ? (
          <Text>Observação da agência: {content.waiting_note}</Text>
        ) : null}
        {content.latest_reason ? <Text>Último pedido de ajuste: {content.latest_reason}</Text> : null}
        {mode === "admin" && content.internal_notes ? <Text size="sm">Nota interna: {content.internal_notes}</Text> : null}
        <Group>
          {mode === "admin" && content.status !== "published" && content.status !== "cancelled" ? (
            <Button component="a" href={`${base}/contents/${content.id}/edit`} onClick={(event) => { event.preventDefault(); router.push(`${base}/contents/${content.id}/edit`); }}>
              Editar
            </Button>
          ) : null}
          {mode === "admin" && (content.status === "draft" || content.status === "in_progress") ? (
            <Button onClick={() => void act(`/api/contents/${content.id}/submit`, "Enviado para aprovação.")}>Enviar para aprovação</Button>
          ) : null}
          {mode === "admin" && content.status === "changes_requested" ? (
            <Button variant="default" onClick={() => void act(`/api/contents/${content.id}/review`, "Revisão iniciada.")}>
              Iniciar revisão
            </Button>
          ) : null}
          {mode === "admin" && (content.status === "in_review" || content.status === "changes_requested") ? (
            <Button onClick={() => void act(`/api/contents/${content.id}/resubmit`, "Reenviado para aprovação.")}>Reenviar</Button>
          ) : null}
          {mode === "admin" && content.status === "approved" ? (
            <Button color="teal" onClick={() => void act(`/api/contents/${content.id}/publish`, "Marcado como publicado.")}>
              Marcar publicado
            </Button>
          ) : null}
          {mode === "admin" && content.status !== "cancelled" && content.status !== "published" ? (
            <Button color="gray" variant="light" onClick={() => void act(`/api/contents/${content.id}/cancel`, "Conteúdo cancelado.")}>
              Cancelar
            </Button>
          ) : null}
          {mode === "admin" ? (
            <Button
              color="red"
              variant="subtle"
              onClick={() => {
                if (!window.confirm("Excluir este conteúdo? O histórico permanece no banco.")) return;
                void api(`/api/contents/${content.id}`, { method: "DELETE" })
                  .then(() => router.push("/admin/contents"))
                  .catch(fail);
              }}
            >
              Excluir
            </Button>
          ) : null}
          {mode === "client" && (content.status === "pending_approval" || content.status === "resubmitted") ? (
            <Button onClick={() => router.push("/portal/approve")}>Ir para aprovação</Button>
          ) : null}
        </Group>
      </Stack>
      <Stack>
        <Title order={4}>Histórico</Title>
        {history.map((event) => (
          <div key={event.id} className="timeline-card">
            <Text fw={600}>{ACTIONS[event.action] ?? event.action}</Text>
            <Text size="sm" c="dimmed">
              {event.actor_name} · {formatWhen(event.created_at)}
              {event.version ? ` · versão ${event.version}` : ""}
            </Text>
            {event.reason ? <Text size="sm" mt={6}>{event.reason}</Text> : null}
          </div>
        ))}
      </Stack>
    </SimpleGrid>
  );
}
