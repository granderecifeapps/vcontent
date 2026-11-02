"use client";

import { DatesReady } from "./dates";
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { AuthProvider } from "@/lib/auth";
import { theme } from "@/theme";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <MantineProvider theme={theme} forceColorScheme="light">
      <Notifications position="top-right" />
      <AuthProvider>
        <DatesReady>{children}</DatesReady>
      </AuthProvider>
    </MantineProvider>
  );
}
