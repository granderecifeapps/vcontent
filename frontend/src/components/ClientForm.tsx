"use client";

import { Button, Group, Select, SimpleGrid, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { Dropzone, IMAGE_MIME_TYPE } from "@mantine/dropzone";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, uploadForm } from "@/lib/api";
import { fail, ok } from "@/lib/feedback";
import type { Client } from "@/lib/types";

export function ClientForm({ initial }: { initial?: Client | null }) {
  const router = useRouter();
  const [company, setCompany] = useState(initial?.company_name ?? "");
  const [contact, setContact] = useState(initial?.contact_name ?? "");
  const [email, setEmail] = useState(initial?.email ?? "");
  const [phone, setPhone] = useState(initial?.phone ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [notes, setNotes] = useState(initial?.internal_notes ?? "");
  const [status, setStatus] = useState(initial?.status ?? "active");
  const [accessName, setAccessName] = useState(initial?.access?.full_name ?? "");
  const [accessEmail, setAccessEmail] = useState(initial?.access?.email ?? "");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    try {
      const body: Record<string, string | null> = {
        company_name: company.trim(),
        contact_name: contact.trim(),
        email: email.trim(),
        phone: phone.trim() || null,
        description: description.trim() || null,
        internal_notes: notes.trim() || null,
        status,
        access_name: (accessName || contact).trim(),
        access_email: (accessEmail || email).trim(),
      };
      if (!initial || password) body.access_password = password;
      if (initial) {
        await api(`/api/clients/${initial.id}`, { method: "PATCH", body: JSON.stringify(body) });
        ok("Cliente atualizado.");
        router.push(`/admin/clients/${initial.id}`);
      } else {
        const created = await api<Client>("/api/clients", { method: "POST", body: JSON.stringify(body) });
        ok("Cliente cadastrado. O acesso já pode entrar.");
        router.push(`/admin/clients/${created.id}`);
      }
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Stack>
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <TextInput label="Empresa" value={company} onChange={(event) => setCompany(event.currentTarget.value)} required />
        <TextInput label="Responsável" value={contact} onChange={(event) => setContact(event.currentTarget.value)} required />
        <TextInput label="E-mail de contato" value={email} onChange={(event) => setEmail(event.currentTarget.value)} required />
        <TextInput label="Telefone" value={phone} onChange={(event) => setPhone(event.currentTarget.value)} />
      </SimpleGrid>
      <Textarea label="Descrição" minRows={3} value={description} onChange={(event) => setDescription(event.currentTarget.value)} />
      <Textarea label="Observações internas" minRows={3} value={notes} onChange={(event) => setNotes(event.currentTarget.value)} />
      <Select
        label="Status"
        data={[
          { value: "active", label: "Ativo" },
          { value: "inactive", label: "Inativo" },
        ]}
        value={status}
        onChange={(value) => setStatus((value as "active" | "inactive") || "active")}
      />
      <Text fw={600}>Acesso do cliente</Text>
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <TextInput label="Nome de login" value={accessName} onChange={(event) => setAccessName(event.currentTarget.value)} placeholder="Igual ao responsável, se vazio" />
        <TextInput label="E-mail de login" value={accessEmail} onChange={(event) => setAccessEmail(event.currentTarget.value)} placeholder="Igual ao contato, se vazio" />
        <TextInput
          type="password"
          label={initial ? "Nova senha" : "Senha inicial"}
          description={initial ? "Deixe em branco para manter a atual." : "Mínimo de 8 caracteres. Entregue ao cliente por um canal seguro."}
          value={password}
          onChange={(event) => setPassword(event.currentTarget.value)}
        />
      </SimpleGrid>
      {initial ? <LogoField client={initial} /> : null}
      <Group>
        <Button loading={busy} onClick={() => void save()}>
          Salvar cliente
        </Button>
      </Group>
    </Stack>
  );
}

function LogoField({ client }: { client: Client }) {
  const [logo, setLogo] = useState(client.logo_url);
  return (
    <Stack gap="xs">
      <Text fw={600}>Logotipo</Text>
      {logo ? <img src={logo} alt="" style={{ width: 88, height: 88, objectFit: "cover", borderRadius: 16 }} /> : null}
      <Dropzone
        accept={IMAGE_MIME_TYPE}
        maxSize={5 * 1024 * 1024}
        onDrop={(files) => {
          const body = new FormData();
          body.append("file", files[0]);
          void uploadForm<Client>(`/api/clients/${client.id}/logo`, body)
            .then((updated) => {
              setLogo(updated.logo_url);
              ok("Logotipo atualizado.");
            })
            .catch(fail);
        }}
      >
        <Text size="sm" c="dimmed" ta="center">
          Envie JPG, PNG ou WEBP de até 5 MB
        </Text>
      </Dropzone>
      {logo ? (
        <Button
          variant="subtle"
          color="red"
          onClick={() =>
            void api<Client>(`/api/clients/${client.id}/logo`, { method: "DELETE" })
              .then(() => setLogo(null))
              .catch(fail)
          }
        >
          Remover logotipo
        </Button>
      ) : null}
    </Stack>
  );
}
