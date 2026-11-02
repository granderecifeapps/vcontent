"use client";

import { Stack, Text } from "@mantine/core";
import { useEffect, useState } from "react";
import { ContractReader } from "@/components/ContractReader";
import { LoadBox, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { fail } from "@/lib/feedback";

type Contract = { filename: string | null; url: string | null; uploaded_at: string | null } | null;

export default function ContractPage() {
  const [data, setData] = useState<{ company_name: string; contract: Contract } | null>(null);
  useEffect(() => {
    void api<{ company_name: string; contract: Contract }>("/api/contract").then(setData).catch(fail);
  }, []);
  if (!data) return <LoadBox />;
  return (
    <Stack>
      <PageHeader kicker={data.company_name} title="Contrato" description="Leitura do contrato enviado pela agência. O arquivo fica salvo aqui." />
      {data.contract?.url ? (
        <ContractReader filename={data.contract.filename} url={data.contract.url} uploadedAt={data.contract.uploaded_at} />
      ) : (
        <Text c="dimmed">A agência ainda não enviou o contrato.</Text>
      )}
    </Stack>
  );
}
