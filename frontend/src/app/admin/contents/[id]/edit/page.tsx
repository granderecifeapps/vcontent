"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ContentForm } from "@/components/ContentForm";
import { LoadBox, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { fail } from "@/lib/feedback";
import type { Content } from "@/lib/types";

export default function EditContentPage() {
  const params = useParams<{ id: string }>();
  const [content, setContent] = useState<Content | null>(null);
  useEffect(() => {
    void api<Content>(`/api/contents/${params.id}`).then(setContent).catch(fail);
  }, [params.id]);
  if (!content) return <LoadBox />;
  return (
    <>
      <PageHeader kicker="Peças" title={`Editar ${content.title}`} description="Se o cliente já tinha visto esta peça, salvar uma alteração de material abre uma nova revisão." />
      <ContentForm initial={content} />
    </>
  );
}
