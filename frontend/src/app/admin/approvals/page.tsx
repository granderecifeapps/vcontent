"use client";

import { Tabs } from "@mantine/core";
import { ContentCollection } from "@/components/ContentCollection";
import { PageHeader } from "@/components/ui";

export default function ApprovalsPage() {
  return (
    <>
      <PageHeader kicker="Fluxo" title="Aprovações" description="O que espera o cliente, o que voltou com ajuste e o que já pode ser publicado." />
      <Tabs defaultValue="pending">
        <Tabs.List>
          <Tabs.Tab value="pending">Aguardando</Tabs.Tab>
          <Tabs.Tab value="changes">Ajustes</Tabs.Tab>
          <Tabs.Tab value="approved">Aprovados</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="pending" pt="md">
          <ContentCollection status="pending_approval,resubmitted" hrefBase="/admin/contents" empty="Nenhum conteúdo na fila do cliente." />
        </Tabs.Panel>
        <Tabs.Panel value="changes" pt="md">
          <ContentCollection status="changes_requested,in_review" hrefBase="/admin/contents" empty="Nenhum ajuste em aberto." />
        </Tabs.Panel>
        <Tabs.Panel value="approved" pt="md">
          <ContentCollection status="approved" hrefBase="/admin/contents" empty="Nada aprovado aguardando publicação." />
        </Tabs.Panel>
      </Tabs>
    </>
  );
}
