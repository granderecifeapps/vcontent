"use client";

import { ContentCollection } from "@/components/ContentCollection";
import { PageHeader } from "@/components/ui";

export default function ProgressPage() {
  return (
    <>
      <PageHeader
        kicker="Fila da agência"
        title="Em andamento"
        description="Publicações que ainda dependem de material seu. A observação diz o que falta enviar."
      />
      <ContentCollection
        status="in_progress"
        hrefBase="/portal/contents"
        audience="client"
        empty="Nenhuma publicação aguardando o seu material."
      />
    </>
  );
}
