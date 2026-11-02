"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ClientForm } from "@/components/ClientForm";
import { LoadBox, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { fail } from "@/lib/feedback";
import type { Client } from "@/lib/types";

export default function EditClientPage() {
  const params = useParams<{ id: string }>();
  const [client, setClient] = useState<Client | null>(null);
  useEffect(() => {
    void api<Client>(`/api/clients/${params.id}`).then(setClient).catch(fail);
  }, [params.id]);
  if (!client) return <LoadBox />;
  return (
    <>
      <PageHeader kicker="Contas" title={`Editar ${client.company_name}`} />
      <ClientForm initial={client} />
    </>
  );
}
