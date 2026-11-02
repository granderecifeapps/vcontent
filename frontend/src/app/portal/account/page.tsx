"use client";

import { Button, Stack, Text, TextInput, PasswordInput, Title } from "@mantine/core";
import Link from "next/link";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fail, ok } from "@/lib/feedback";
import { formatWhen } from "@/lib/labels";
import type { Notice, Page } from "@/lib/types";

export default function AccountPage() {
  const { user, refresh } = useAuth();
  const [name, setName] = useState(user?.full_name ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [notes, setNotes] = useState<Notice[]>([]);

  useEffect(() => {
    void api<Page<Notice> & { unread_count: number }>("/api/notifications?page_size=20").then((page) => setNotes(page.items)).catch(fail);
  }, []);

  return (
    <Stack maw={560}>
      <PageHeader kicker="Conta" title="Minha conta" description={user?.client?.company_name} />
      <TextInput label="Nome" value={name} onChange={(event) => setName(event.currentTarget.value)} />
      <TextInput label="Telefone" value={phone} onChange={(event) => setPhone(event.currentTarget.value)} />
      <Button
        onClick={() =>
          void api("/api/auth/profile", { method: "PATCH", body: JSON.stringify({ full_name: name, phone }) })
            .then(() => {
              ok("Dados atualizados.");
              return refresh();
            })
            .catch(fail)
        }
      >
        Salvar
      </Button>
      <Title order={4}>Senha</Title>
      <PasswordInput label="Senha atual" value={current} onChange={(event) => setCurrent(event.currentTarget.value)} />
      <PasswordInput label="Nova senha" value={next} onChange={(event) => setNext(event.currentTarget.value)} />
      <Button
        variant="default"
        onClick={() =>
          void api("/api/auth/change-password", { method: "POST", body: JSON.stringify({ current_password: current, new_password: next }) })
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
      <Title order={4} id="avisos">
        Avisos
      </Title>
      {notes.map((item) => (
        <div key={item.id}>
          <Text fw={600}>{item.title}</Text>
          <Text size="sm">{item.body}</Text>
          <Text size="xs" c="dimmed">
            {formatWhen(item.created_at)}
          </Text>
          {item.data?.content_id ? (
            <Text component={Link} href={`/portal/contents/${item.data.content_id}`} c="brand" size="sm">
              Abrir conteúdo
            </Text>
          ) : null}
        </div>
      ))}
      {!notes.length ? <Text c="dimmed">Sem avisos.</Text> : null}
    </Stack>
  );
}
