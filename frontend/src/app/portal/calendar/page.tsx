"use client";

import { CalendarBoard } from "@/components/CalendarBoard";
import { PageHeader } from "@/components/ui";

export default function PortalCalendar() {
  return (
    <>
      <PageHeader kicker="Planejamento" title="Calendário" description="As datas combinadas com a agência." />
      <CalendarBoard baseHref="/portal/contents" />
    </>
  );
}
