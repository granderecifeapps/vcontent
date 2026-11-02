"use client";

import { ActionIcon, AppShell, Avatar, Group, Indicator, Menu, Text } from "@mantine/core";
import { IconBell, IconCalendar, IconChecks, IconFileText, IconHistory, IconHome, IconHourglass, IconLogout, IconPencil, IconThumbUp, IconUser } from "@tabler/icons-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Logo } from "./Logo";
import { LoadBox } from "./ui";

const links = [
  { href: "/portal", label: "Início", icon: IconHome },
  { href: "/portal/approve", label: "Aprovar", icon: IconThumbUp },
  { href: "/portal/progress", label: "Em andamento", icon: IconHourglass },
  { href: "/portal/calendar", label: "Calendário", icon: IconCalendar },
  { href: "/portal/approved", label: "Aprovados", icon: IconChecks },
  { href: "/portal/changes", label: "Ajustes", icon: IconPencil },
  { href: "/portal/history", label: "Histórico", icon: IconHistory },
  { href: "/portal/contract", label: "Contrato", icon: IconFileText },
  { href: "/portal/account", label: "Minha conta", icon: IconUser },
];

export function PortalShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, ready } = useAuth();
  const [unread, setUnread] = useState(0);
  const immersive = pathname.startsWith("/portal/approve");

  useEffect(() => {
    if (!ready) return;
    if (!user) router.replace("/login");
    else if (user.role !== "client") router.replace("/admin");
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

  if (!ready || !user || user.role !== "client") return <LoadBox />;

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  return (
    <AppShell header={{ height: 64 }} navbar={{ width: 240, breakpoint: "sm", collapsed: { mobile: true } }} padding={immersive ? "sm" : "lg"} styles={{ main: { background: "#f8f7fb" }, navbar: { borderColor: "#eceaf2" } }}>
      <AppShell.Header style={{ background: "rgba(248,247,251,0.92)", backdropFilter: "blur(16px)", borderColor: "#eceaf2" }}>
        <Group h="100%" px="md" justify="space-between">
          <Logo />
          <Group>
            <Indicator disabled={unread === 0} label={unread} size={16} color="brand">
              <ActionIcon variant="subtle" component={Link} href="/portal/account" aria-label="Avisos e conta">
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
                <Menu.Label>{user.client?.company_name || user.full_name}</Menu.Label>
                <Menu.Item component={Link} href="/portal/account">
                  Minha conta
                </Menu.Item>
                <Menu.Item color="red" leftSection={<IconLogout size={16} />} onClick={() => void logout()}>
                  Sair
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="md" visibleFrom="sm">
        <Text size="xs" c="dimmed" tt="uppercase" fw={700} mb="sm">
          {user.client?.company_name}
        </Text>
        <nav className="portal-nav" style={{ display: "grid", gap: 4 }}>
          {links.map((link) => {
            const Icon = link.icon;
            const active = link.href === "/portal" ? pathname === "/portal" : pathname.startsWith(link.href);
            return (
              <Link key={link.href} href={link.href} data-active={active}>
                <Icon size={18} />
                {link.label}
              </Link>
            );
          })}
        </nav>
      </AppShell.Navbar>
      <AppShell.Main>
        <nav className="mobile-tabs" hidden={immersive} style={{ marginBottom: 16 }} aria-label="Seções">
          {links.map((link) => {
            const active = link.href === "/portal" ? pathname === "/portal" : pathname.startsWith(link.href);
            return (
              <Link key={link.href} href={link.href} data-active={active}>
                {link.label}
              </Link>
            );
          })}
        </nav>
        <style>{`@media (min-width: 48em) { .mobile-tabs { display: none !important; } }`}</style>
        {children}
      </AppShell.Main>
    </AppShell>
  );
}
