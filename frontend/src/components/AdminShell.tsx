"use client";

import { ActionIcon, AppShell, Avatar, Burger, Group, Indicator, Menu, Text } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  IconBell,
  IconCalendar,
  IconChecks,
  IconLayoutDashboard,
  IconLogout,
  IconPhoto,
  IconSettings,
  IconUsers,
} from "@tabler/icons-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Logo } from "./Logo";
import { LoadBox } from "./ui";

const links = [
  { href: "/admin", label: "Dashboard", icon: IconLayoutDashboard },
  { href: "/admin/clients", label: "Clientes", icon: IconUsers },
  { href: "/admin/contents", label: "Conteúdos", icon: IconPhoto },
  { href: "/admin/calendar", label: "Calendário", icon: IconCalendar },
  { href: "/admin/approvals", label: "Aprovações", icon: IconChecks },
  { href: "/admin/notifications", label: "Notificações", icon: IconBell },
  { href: "/admin/settings", label: "Configurações", icon: IconSettings },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const [opened, { toggle, close }] = useDisclosure();
  const pathname = usePathname();
  const router = useRouter();
  const { user, ready } = useAuth();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!ready) return;
    if (!user) router.replace("/login");
    else if (user.role !== "admin") router.replace("/portal");
  }, [ready, user, router]);

  useEffect(() => {
    if (!user) return;
    let stop = false;
    const load = () =>
      api<{ unread_count: number }>("/api/notifications?page_size=1")
        .then((data) => {
          if (!stop) setUnread(data.unread_count);
        })
        .catch(() => undefined);
    void load();
    const timer = window.setInterval(load, 30000);
    return () => {
      stop = true;
      window.clearInterval(timer);
    };
  }, [user, pathname]);

  if (!ready || !user || user.role !== "admin") return <LoadBox />;

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  return (
    <AppShell
      header={{ height: 64 }}
      navbar={{ width: 248, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="lg"
      styles={{
        header: { background: "rgba(248,247,251,0.9)", borderColor: "#eceaf2", backdropFilter: "blur(16px)" },
        navbar: { background: "#16141c", borderColor: "#16141c", color: "#f7f3ff" },
        main: { background: "#f8f7fb" },
      }}
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="Abrir menu" />
            <Text fw={600} visibleFrom="sm">
              Operação
            </Text>
          </Group>
          <Group>
            <Indicator disabled={unread === 0} label={unread} size={16} color="brand">
              <ActionIcon variant="subtle" component={Link} href="/admin/notifications" aria-label="Notificações">
                <IconBell size={20} />
              </ActionIcon>
            </Indicator>
            <Menu position="bottom-end">
              <Menu.Target>
                <Avatar radius="xl" color="brand" style={{ cursor: "pointer" }}>
                  {user.full_name.slice(0, 1)}
                </Avatar>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>{user.full_name}</Menu.Label>
                <Menu.Item component={Link} href="/admin/settings">
                  Configurações
                </Menu.Item>
                <Menu.Item color="red" leftSection={<IconLogout size={16} />} onClick={() => void logout()}>
                  Sair
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="md">
        <Logo light />
        <nav className="shell-nav" style={{ marginTop: 28, display: "grid", gap: 4 }}>
          {links.map((link) => {
            const Icon = link.icon;
            const active = link.href === "/admin" ? pathname === "/admin" : pathname.startsWith(link.href);
            return (
              <Link key={link.href} href={link.href} data-active={active} onClick={close}>
                <Icon size={18} />
                {link.label}
              </Link>
            );
          })}
        </nav>
      </AppShell.Navbar>
      <AppShell.Main>{children}</AppShell.Main>
    </AppShell>
  );
}
