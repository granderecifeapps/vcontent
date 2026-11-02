"use client";

import { ContentCollection } from "@/components/ContentCollection";
import { PageHeader } from "@/components/ui";

export default function ApprovedPage() {
  return (
    <>
      <PageHeader kicker="Feitos" title="Aprovados" />
      <ContentCollection status="approved,published" hrefBase="/portal/contents" empty="Você ainda não aprovou conteúdos." />
    </>
  );
}
