"use client";

import { Stack, Text } from "@mantine/core";
import { useEffect, useState } from "react";
import { fetchBinary } from "@/lib/api";
import { formatWhen } from "@/lib/labels";
import { LoadBox } from "./ui";

export function ContractReader({
  filename,
  url,
  uploadedAt,
}: {
  filename?: string | null;
  url: string;
  uploadedAt?: string | null;
}) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let objectUrl = "";
    setSrc(null);
    setError(null);
    void fetchBinary(url)
      .then((data) => {
        objectUrl = URL.createObjectURL(new Blob([data], { type: "application/pdf" }));
        if (active) setSrc(objectUrl);
      })
      .catch(() => {
        if (active) setError("Não foi possível abrir o contrato. Atualize a página e tente de novo.");
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [url]);

  return (
    <Stack gap="sm">
      <Text size="sm" c="dimmed">
        {filename || "Contrato"}
        {uploadedAt ? ` · enviado em ${formatWhen(uploadedAt)}` : ""} · somente leitura
      </Text>
      {error ? <Text c="red">{error}</Text> : null}
      {src ? (
        <iframe title={filename || "Contrato"} src={src} style={{ width: "100%", height: "72vh", border: "1px solid #eceaf2", borderRadius: 16, background: "#fff" }} />
      ) : error ? null : (
        <LoadBox />
      )}
    </Stack>
  );
}
