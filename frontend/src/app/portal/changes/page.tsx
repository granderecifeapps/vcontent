"use client";

import { ContentCollection } from "@/components/ContentCollection";
import { PageHeader } from "@/components/ui";

export default function ChangesPage() {
  return (
    <>
      <PageHeader kicker="Em aberto" title="Ajustes solicitados" description="A justificativa que você enviou continua visível." />
      <ContentCollection status="changes_requested,in_review" hrefBase="/portal/contents" empty="Nenhum conteúdo esperando ajuste." />
    </>
  );
}
