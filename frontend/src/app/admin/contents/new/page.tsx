"use client";

import { ContentForm } from "@/components/ContentForm";
import { PageHeader } from "@/components/ui";

export default function NewContentPage() {
  return (
    <>
      <PageHeader kicker="Peças" title="Novo conteúdo" description="O formulário muda conforme a plataforma e o formato." />
      <ContentForm />
    </>
  );
}
