"use client";

import { Anchor, Button, Paper, PasswordInput, Stack, Text, TextInput, Title } from "@mantine/core";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Logo } from "@/components/Logo";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fail } from "@/lib/feedback";
import type { User } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const result = await api<{ user: User }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setUser(result.user);
      router.replace(result.user.role === "admin" ? "/admin" : "/portal");
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", display: "grid", gridTemplateColumns: "minmax(0, 1.1fr) minmax(320px, 460px)" }} className="auth-grid">
      <section style={{ display: "none" }} className="auth-side">
        <div style={{ maxWidth: 460 }}>
          <Logo light />
          <Title order={1} mt={48} c="white" style={{ fontSize: "4rem", letterSpacing: "-0.06em", lineHeight: 0.95 }}>
            O conteúdo, no ritmo da aprovação.
          </Title>
          <Text c="#f6f1ea" mt="md" size="lg">
            Clientes, peças, calendário e o sim ou o ajuste — sem planilha e sem grupo perdido.
          </Text>
        </div>
      </section>
      <section style={{ display: "grid", placeItems: "center", padding: 24 }}>
        <Paper p="xl" radius={28} withBorder w="100%" maw={420} component="form" onSubmit={(event) => void submit(event)}>
          <Logo />
          <Title order={2} mt="lg">
            Entrar
          </Title>
          <Text c="dimmed" mb="lg">
            Use o acesso da agência ou o acesso enviado ao cliente.
          </Text>
          <Stack>
            <TextInput label="E-mail" type="email" value={email} onChange={(event) => setEmail(event.currentTarget.value)} required />
            <PasswordInput label="Senha" value={password} onChange={(event) => setPassword(event.currentTarget.value)} required />
            <Button type="submit" loading={busy}>
              Entrar
            </Button>
            <Anchor component={Link} href="/forgot-password" size="sm">
              Esqueci minha senha
            </Anchor>
          </Stack>
        </Paper>
      </section>
      <style>{`
        @media (min-width: 900px) {
          .auth-side { display: flex !important; align-items: flex-end; padding: 64px; background: #7a3040; }
        }
        @media (max-width: 899px) {
          .auth-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </main>
  );
}
