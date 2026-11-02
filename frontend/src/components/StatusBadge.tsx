import { Badge } from "@mantine/core";
import { STATUS } from "@/lib/labels";

export function StatusBadge({ status, audience = "admin" }: { status: string; audience?: "admin" | "client" }) {
  const item = STATUS[status] ?? { label: status, color: "gray" };
  const label = status === "in_progress" && audience === "client" ? "Aguardando cliente" : item.label;
  return (
    <Badge variant="light" color={item.color} radius="xl">
      {label}
    </Badge>
  );
}
