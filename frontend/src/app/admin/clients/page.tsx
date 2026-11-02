"use client";

import { Badge, Button, Group, Table, Text, TextInput } from "@mantine/core";
import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState, LoadBox, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { fail } from "@/lib/feedback";
import type { Client, Page } from "@/lib/types";

export default function ClientsPage() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState<Page<Client> | null>(null);
  useEffect(() => {
    const params = new URLSearchParams({ page_size: "50" });
    if (q.trim()) params.set("q", q.trim());
    const timer = window.setTimeout(() => {
      void api<Page<Client>>(`/api/clients?${params.toString()}`).then(setPage).catch(fail);
    }, 200);
    return () => window.clearTimeout(timer);
  }, [q]);
  return (
    <>
      <PageHeader
        kicker="Contas"
        title="Clientes"
        description="Cada cliente entra com a própria conta e só vê o que é dele."
        action={
          <Button component={Link} href="/admin/clients/new">
            Novo cliente
          </Button>
        }
      />
      <TextInput placeholder="Buscar empresa, responsável ou e-mail" value={q} onChange={(event) => setQ(event.currentTarget.value)} mb="md" />
      {!page ? (
        <LoadBox />
      ) : page.items.length === 0 ? (
        <EmptyState title="Nenhum cliente" text="Cadastre a primeira conta para começar o calendário." action={<Button component={Link} href="/admin/clients/new">Cadastrar</Button>} />
      ) : (
        <Table.ScrollContainer minWidth={720}>
          <Table highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Empresa</Table.Th>
                <Table.Th>Responsável</Table.Th>
                <Table.Th>Acesso</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {page.items.map((item) => (
                <Table.Tr key={item.id}>
                  <Table.Td>
                    <Text component={Link} href={`/admin/clients/${item.id}`} fw={600}>
                      {item.company_name}
                    </Text>
                  </Table.Td>
                  <Table.Td>{item.contact_name}</Table.Td>
                  <Table.Td>{item.access?.email}</Table.Td>
                  <Table.Td>
                    <Badge variant="light" color={item.status === "active" ? "green" : "gray"}>
                      {item.status === "active" ? "Ativo" : "Inativo"}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
      <Group mt="md" />
    </>
  );
}
