"use client";

import { Button, Group, Select, TextInput } from "@mantine/core";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ContentCollection } from "@/components/ContentCollection";
import { PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { STATUS } from "@/lib/labels";
import type { Client, Page, Platform } from "@/lib/types";

export default function ContentsPage() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [clientId, setClientId] = useState<string | null>(null);
  const [platformId, setPlatformId] = useState<string | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [query, setQuery] = useState("");

  useEffect(() => {
    void Promise.all([api<Page<Client>>("/api/clients?page_size=100"), api<Platform[]>("/api/platforms")]).then(([clientPage, platformPage]) => {
      setClients(clientPage.items);
      setPlatforms(platformPage);
    });
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    if (q.trim()) params.set("q", q.trim());
    if (status) params.set("status", status);
    if (clientId) params.set("client_id", clientId);
    if (platformId) params.set("platform_id", platformId);
    setQuery(params.toString());
  }, [q, status, clientId, platformId]);

  return (
    <>
      <PageHeader
        kicker="Peças"
        title="Conteúdos"
        description="Rascunho, aprovação e republicação ficam no mesmo lugar."
        action={
          <Button component={Link} href="/admin/contents/new">
            Novo conteúdo
          </Button>
        }
      />
      <Group mb="md" grow>
        <TextInput placeholder="Buscar título, legenda ou copy" value={q} onChange={(event) => setQ(event.currentTarget.value)} />
        <Select placeholder="Status" clearable data={Object.entries(STATUS).map(([value, item]) => ({ value, label: item.label }))} value={status} onChange={setStatus} />
        <Select placeholder="Cliente" clearable data={clients.map((item) => ({ value: item.id, label: item.company_name }))} value={clientId} onChange={setClientId} />
        <Select placeholder="Plataforma" clearable data={platforms.map((item) => ({ value: item.id, label: item.name }))} value={platformId} onChange={setPlatformId} />
      </Group>
      <ContentCollection hrefBase="/admin/contents" empty="Nenhum conteúdo com esses filtros." query={query} />
    </>
  );
}
