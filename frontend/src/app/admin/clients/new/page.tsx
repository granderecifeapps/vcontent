"use client";

import { ClientForm } from "@/components/ClientForm";
import { PageHeader } from "@/components/ui";

export default function NewClientPage() {
  return (
    <>
      <PageHeader kicker="Contas" title="Novo cliente" description="O acesso é criado junto com a ficha." />
      <ClientForm />
    </>
  );
}
