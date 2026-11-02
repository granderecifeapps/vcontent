"use client";

import { Anchor, Button, Paper, Stack, Text, TextInput, Title } from "@mantine/core";
import Link from "next/link";
import { useState } from "react";
import { Logo } from "@/components/Logo";
import { api } from "@/lib/api";
import { fail, ok } from "@/lib/feedback";

export default function ForgotPage() {
  const [email, setEmail] = useState("");
  const [link, setLink] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const result = await api<{ detail: string; dev_reset_url?: string }>("/api/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      ok(result.detail);
      setLink(result.dev_reset_url ?? null);
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24 }}>
      <Paper p="xl" radius={28} withBorder w="100%" maw={440} component="form" onSubmit={(event) => void submit(event)}>
        <Logo />
        <Title order={2} mt="lg">
          Recuperar senha
        </Title>
        <Text c="dimmed" mb="lg">
          Se o e-mail existir, preparamos um link de redefinição. Nesta instalação local, o link aparece aqui.
        </Text>
        <Stack>
          <TextInput label="E-mail" type="email" value={email} onChange={(event) => setEmail(event.currentTarget.value)} required />
          <Button type="submit" loading={busy}>
            Enviar
          </Button>
          {link ? (
            <Anchor href={link} size="sm">
              Abrir redefinição
            </Anchor>
          ) : null}
          <Anchor component={Link} href="/login" size="sm">
            Voltar ao login
          </Anchor>
        </Stack>
      </Paper>
    </main>
  );
}
