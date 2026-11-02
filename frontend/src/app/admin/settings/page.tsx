"use client";

import { Button, SimpleGrid, Stack, Table, Text, TextInput, PasswordInput, Title } from "@mantine/core";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fail, ok } from "@/lib/feedback";
import { formatWhen } from "@/lib/labels";

type Audit = { id: string; action: string; entity_type: string; actor_name: string | null; created_at: string; ip: string | null };
type System = { version: string; environment: string; database: string; storage: string; storage_backend?: string; drive_account_email?: string; prepared_channels: string[] };

export default function SettingsPage() {
  const { user, refresh } = useAuth();
  const [name, setName] = useState(user?.full_name ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [system, setSystem] = useState<System | null>(null);
  const [audit, setAudit] = useState<Audit[]>([]);

  useEffect(() => {
    void Promise.all([api<System>("/api/system"), api<{ items: Audit[] }>("/api/audit?page_size=20")]).then(([info, log]) => {
      setSystem(info);
      setAudit(log.items);
    }).catch(fail);
  }, []);

  return (
    <Stack>
      <PageHeader kicker="Conta" title="Configurações" description="Perfil da administradora, senha e o registro de auditoria." />
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <Stack>
          <Title order={4}>Perfil</Title>
          <TextInput label="Nome" value={name} onChange={(event) => setName(event.currentTarget.value)} />
          <TextInput label="Telefone" value={phone} onChange={(event) => setPhone(event.currentTarget.value)} />
          <Button
            onClick={() =>
              void api("/api/auth/profile", { method: "PATCH", body: JSON.stringify({ full_name: name, phone }) })
                .then(() => {
                  ok("Perfil atualizado.");
                  return refresh();
                })
                .catch(fail)
            }
          >
            Salvar perfil
          </Button>
        </Stack>
        <Stack>
          <Title order={4}>Senha</Title>
          <PasswordInput label="Senha atual" value={current} onChange={(event) => setCurrent(event.currentTarget.value)} />
          <PasswordInput label="Nova senha" value={next} onChange={(event) => setNext(event.currentTarget.value)} />
          <Button
            variant="default"
            onClick={() =>
              void api("/api/auth/change-password", {
                method: "POST",
                body: JSON.stringify({ current_password: current, new_password: next }),
              })
                .then(() => {
                  setCurrent("");
                  setNext("");
                  ok("Senha atualizada.");
                })
                .catch(fail)
            }
          >
            Trocar senha
          </Button>
        </Stack>
      </SimpleGrid>
      {system ? (
        <Stack gap={4}>
          <Text c="dimmed">
            Versão {system.version} · banco {system.database} · storage {system.storage} · canais preparados: {system.prepared_channels.join(", ")}
          </Text>
          <Text c="dimmed">
            {system.storage_backend === "google_drive"
              ? `Imagens e vídeos ficam no Google Drive${system.drive_account_email ? ` de ${system.drive_account_email}` : ""}.`
              : "Imagens e vídeos ainda usam o armazenamento atual. O Google Drive entra no lugar assim que a conta for autorizada."}
          </Text>
        </Stack>
      ) : null}
      <Title order={4}>Auditoria</Title>
      <Table.ScrollContainer minWidth={640}>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Quando</Table.Th>
              <Table.Th>Ação</Table.Th>
              <Table.Th>Quem</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {audit.map((item) => (
              <Table.Tr key={item.id}>
                <Table.Td>{formatWhen(item.created_at)}</Table.Td>
                <Table.Td>
                  {item.action} · {item.entity_type}
                </Table.Td>
                <Table.Td>{item.actor_name || "—"}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Stack>
  );
}
