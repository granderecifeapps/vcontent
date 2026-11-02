"use client";

import { CalendarBoard } from "@/components/CalendarBoard";
import { PageHeader } from "@/components/ui";

export default function CalendarPage() {
  return (
    <>
      <PageHeader kicker="Planejamento" title="Calendário editorial" description="TikTok em escuro, Instagram em lilás. Filtre por cliente e plataforma." />
      <CalendarBoard baseHref="/admin/contents" showClientFilter />
    </>
  );
}
