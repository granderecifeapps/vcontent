"use client";

import { useParams } from "next/navigation";
import { ContentView } from "@/components/ContentView";

export default function PortalContentPage() {
  const params = useParams<{ id: string }>();
  return <ContentView id={params.id} mode="client" />;
}
