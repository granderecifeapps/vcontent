import { notifications } from "@mantine/notifications";

export function ok(message: string) {
  notifications.show({ message, color: "green", radius: "md" });
}

export function fail(error: unknown) {
  const message = error instanceof Error ? error.message : "Algo saiu do esperado.";
  notifications.show({ message, color: "red", radius: "md" });
}
