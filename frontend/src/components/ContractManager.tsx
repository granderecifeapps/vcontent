"use client";

import { Button, FileButton, Group, Stack, Text } from "@mantine/core";
import { useState } from "react";
import { api, uploadForm } from "@/lib/api";
import { fail, ok } from "@/lib/feedback";
import type { Client } from "@/lib/types";
import { ContractReader } from "./ContractReader";

export function ContractManager({ client, onChange }: { client: Client; onChange: (client: Client) => void }) {
  const [busy, setBusy] = useState(false);
  const contract = client.contract;

  async function upload(file: File | null) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      fail(new Error("Envie um arquivo PDF."));
      return;
    }
    const body = new FormData();
    body.append("file", file);
    setBusy(true);
    try {
      const updated = await uploadForm<Client>(`/api/clients/${client.id}/contract`, body);
      onChange(updated);
      ok("Contrato salvo. O cliente já pode ler no portal.");
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm("Remover o contrato deste cliente?")) return;
    setBusy(true);
    try {
      const updated = await api<Client>(`/api/clients/${client.id}/contract`, { method: "DELETE" });
      onChange(updated);
      ok("Contrato removido.");
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Stack>
      <Group>
        <FileButton onChange={(file) => void upload(file)} accept="application/pdf,.pdf">
          {(props) => (
            <Button {...props} loading={busy}>
              {contract?.url ? "Substituir PDF" : "Enviar contrato em PDF"}
            </Button>
          )}
        </FileButton>
        {contract?.url ? (
          <Button variant="default" color="red" loading={busy} onClick={() => void remove()}>
            Remover
          </Button>
        ) : null}
      </Group>
      <Text size="sm" c="dimmed">
        O arquivo fica associado a este cliente. No portal, a leitura é somente visual.
      </Text>
      {contract?.url ? <ContractReader filename={contract.filename} url={contract.url} uploadedAt={contract.uploaded_at} /> : <Text c="dimmed">Nenhum contrato enviado.</Text>}
    </Stack>
  );
}
