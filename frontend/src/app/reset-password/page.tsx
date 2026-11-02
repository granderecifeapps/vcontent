"use client";

import { Button, Paper, PasswordInput, Stack, Text, Title } from "@mantine/core";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Logo } from "@/components/Logo";
import { api } from "@/lib/api";
import { fail, ok } from "@/lib/feedback";

function ResetForm() {
  const params = useSearchParams();
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api("/api/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token: params.get("token") || "", new_password: password }),
      });
      ok("Senha atualizada.");
      router.replace("/login");
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Paper p="xl" radius={28} withBorder w="100%" maw={440} component="form" onSubmit={(event) => void submit(event)}>
      <Logo />
      <Title order={2} mt="lg">
        Nova senha
      </Title>
      <Text c="dimmed" mb="lg">
        Escolha uma senha com pelo menos 8 caracteres.
      </Text>
      <Stack>
        <PasswordInput label="Nova senha" value={password} onChange={(event) => setPassword(event.currentTarget.value)} required />
        <Button type="submit" loading={busy}>
          Salvar senha
        </Button>
      </Stack>
    </Paper>
  );
}

export default function ResetPage() {
  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24 }}>
      <Suspense>
        <ResetForm />
      </Suspense>
    </main>
  );
}
