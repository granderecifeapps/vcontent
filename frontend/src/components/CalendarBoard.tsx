"use client";

import { Button, Group, Select, Stack, Text } from "@mantine/core";
import dayjs from "dayjs";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { fail } from "@/lib/feedback";
import type { Client, Content, Page, Platform } from "@/lib/types";

type View = "month" | "week" | "day";

export function CalendarBoard({
  baseHref,
  lockedClientId,
  showClientFilter = false,
}: {
  baseHref: string;
  lockedClientId?: string;
  showClientFilter?: boolean;
}) {
  const [view, setView] = useState<View>("month");
  const [anchor, setAnchor] = useState(dayjs());
  const [clientId, setClientId] = useState(lockedClientId ?? "");
  const [platformId, setPlatformId] = useState("");
  const [clients, setClients] = useState<Client[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [items, setItems] = useState<Content[]>([]);

  useEffect(() => {
    const tasks: Promise<unknown>[] = [api<Platform[]>("/api/platforms").then(setPlatforms)];
    if (showClientFilter) tasks.push(api<Page<Client>>("/api/clients?page_size=100").then((page) => setClients(page.items)));
    void Promise.all(tasks).catch(fail);
  }, [showClientFilter]);

  const range = useMemo(() => {
    if (view === "day") return { start: anchor.startOf("day"), end: anchor.endOf("day") };
    if (view === "week") {
      const start = anchor.subtract(anchor.day(), "day").startOf("day");
      return { start, end: start.add(6, "day").endOf("day") };
    }
    const first = anchor.startOf("month");
    const gridStart = first.subtract(first.day(), "day");
    return { start: gridStart, end: gridStart.add(41, "day") };
  }, [anchor, view]);

  useEffect(() => {
    const params = new URLSearchParams({
      start: range.start.format("YYYY-MM-DD"),
      end: range.end.format("YYYY-MM-DD"),
    });
    const selectedClient = lockedClientId || clientId;
    if (selectedClient) params.set("client_id", selectedClient);
    if (platformId) params.set("platform_id", platformId);
    void api<Content[]>(`/api/calendar?${params.toString()}`)
      .then(setItems)
      .catch(fail);
  }, [range.start, range.end, clientId, platformId, lockedClientId]);

  const days = view === "month" ? Array.from({ length: 42 }, (_, index) => range.start.add(index, "day")) : view === "week" ? Array.from({ length: 7 }, (_, index) => range.start.add(index, "day")) : [anchor];

  return (
    <Stack>
      <Group justify="space-between" wrap="wrap">
        <Group>
          <Button variant="default" onClick={() => setAnchor(anchor.subtract(1, view === "month" ? "month" : view === "week" ? "week" : "day"))}>
            Anterior
          </Button>
          <Button variant="default" onClick={() => setAnchor(dayjs())}>
            Hoje
          </Button>
          <Button variant="default" onClick={() => setAnchor(anchor.add(1, view === "month" ? "month" : view === "week" ? "week" : "day"))}>
            Próximo
          </Button>
          <Text fw={600}>{anchor.format("MMMM YYYY")}</Text>
        </Group>
        <Group>
          {(["month", "week", "day"] as View[]).map((item) => (
            <Button key={item} variant={view === item ? "filled" : "default"} onClick={() => setView(item)}>
              {item === "month" ? "Mês" : item === "week" ? "Semana" : "Dia"}
            </Button>
          ))}
        </Group>
      </Group>
      <Group grow>
        {showClientFilter ? (
          <Select
            placeholder="Todos os clientes"
            clearable
            data={clients.map((item) => ({ value: item.id, label: item.company_name }))}
            value={clientId || null}
            onChange={(value) => setClientId(value || "")}
          />
        ) : null}
        <Select
          placeholder="Todas as plataformas"
          clearable
          data={platforms.map((item) => ({ value: item.id, label: item.name }))}
          value={platformId || null}
          onChange={(value) => setPlatformId(value || "")}
        />
      </Group>
      {view !== "day" ? (
        <div className="cal-grid">
          {["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"].slice(0, view === "week" ? 7 : 7).map((label) => (
            <Text key={label} size="xs" c="dimmed" ta="center">
              {label}
            </Text>
          ))}
        </div>
      ) : null}
      <div className={view === "day" ? undefined : "cal-grid"} style={view === "week" ? { marginTop: 8 } : undefined}>
        {days.map((day) => {
          const key = day.format("YYYY-MM-DD");
          const events = items.filter((item) => item.scheduled_date?.slice(0, 10) === key);
          return (
            <div key={key} className={`cal-day ${day.month() === anchor.month() || view !== "month" ? "" : "is-out"} ${day.isSame(dayjs(), "day") ? "is-today" : ""}`} style={view === "day" ? { minHeight: 280 } : undefined}>
              <Text size="xs" fw={700}>
                {day.format("DD")}
              </Text>
              {events.map((item) => (
                <Link key={item.id} href={`${baseHref}/${item.id}`} className={`pill ${item.platform.slug}${item.status === "in_progress" ? " waiting" : ""}`} title={`${item.title} · ${item.status}`}>
                  {item.scheduled_time ? `${item.scheduled_time} ` : ""}
                  {item.title}
                </Link>
              ))}
            </div>
          );
        })}
      </div>
    </Stack>
  );
}
