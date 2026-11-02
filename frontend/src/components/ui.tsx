import { Button, Group, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";

export function PageHeader({
  kicker,
  title,
  description,
  action,
}: {
  kicker?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap">
      <Stack gap={4} style={{ minWidth: 0 }}>
        {kicker ? <p className="kicker">{kicker}</p> : null}
        <Title order={2} style={{ letterSpacing: "-0.04em" }}>
          {title}
        </Title>
        {description ? (
          <Text c="dimmed" maw={620}>
            {description}
          </Text>
        ) : null}
      </Stack>
      {action}
    </Group>
  );
}

export function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div style={{ background: "#fff", border: "1px solid #eceaf2", borderRadius: 20, padding: 18 }}>
      <Text size="sm" c="dimmed">
        {label}
      </Text>
      <p className="stat-value">{value}</p>
    </div>
  );
}

export function EmptyState({ title, text, action }: { title: string; text: string; action?: ReactNode }) {
  return (
    <Stack align="flex-start" gap="xs" p="xl" style={{ background: "#fff", border: "1px dashed #ddd7ea", borderRadius: 20 }}>
      <Title order={4}>{title}</Title>
      <Text c="dimmed" maw={460}>
        {text}
      </Text>
      {action}
    </Stack>
  );
}

export function LoadBox() {
  return (
    <Group justify="center" mih={240}>
      <Button loading variant="subtle">
        Carregando
      </Button>
    </Group>
  );
}
