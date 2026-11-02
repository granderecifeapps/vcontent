"use client";

import { Button, Group, Progress, Select, SimpleGrid, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { Dropzone, IMAGE_MIME_TYPE } from "@mantine/dropzone";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api, uploadWithProgress } from "@/lib/api";
import { fail, ok } from "@/lib/feedback";
import type { Client, Content, Page, Platform } from "@/lib/types";

type PendingFile = { key: string; file: File; url: string };

const VIDEO = ["video/mp4", "video/quicktime"];

export function ContentForm({ initial }: { initial?: Content | null }) {
  const router = useRouter();
  const [clients, setClients] = useState<Client[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [clientId, setClientId] = useState(initial?.client_id ?? "");
  const [platformId, setPlatformId] = useState(initial?.platform.id ?? "");
  const [formatId, setFormatId] = useState(initial?.format.id ?? "");
  const [title, setTitle] = useState(initial?.title ?? "");
  const [caption, setCaption] = useState(initial?.caption ?? "");
  const [copy, setCopy] = useState(initial?.copy_text ?? "");
  const [hashtags, setHashtags] = useState(initial?.hashtags ?? "");
  const [date, setDate] = useState(initial?.scheduled_date?.slice(0, 10) ?? "");
  const [time, setTime] = useState(initial?.scheduled_time ?? "");
  const [internalDescription, setInternalDescription] = useState(initial?.internal_description ?? "");
  const [notes, setNotes] = useState(initial?.internal_notes ?? "");
  const [waitingNote, setWaitingNote] = useState(initial?.waiting_note ?? "");
  const [media, setMedia] = useState(initial?.media ?? []);
  const [pending, setPending] = useState<PendingFile[]>([]);
  const [progress, setProgress] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const contentId = initial?.id;

  useEffect(() => {
    void Promise.all([api<Page<Client>>("/api/clients?page_size=100&status=active"), api<Platform[]>("/api/platforms")])
      .then(([clientPage, platformPage]) => {
        setClients(clientPage.items);
        setPlatforms(platformPage);
        if (!platformId && platformPage[0]) setPlatformId(platformPage[0].id);
      })
      .catch(fail);
  }, [platformId]);

  const platform = platforms.find((item) => item.id === platformId);
  const format = platform?.formats.find((item) => item.id === formatId) ?? platform?.formats[0];

  useEffect(() => {
    if (platform && format && !platform.formats.some((item) => item.id === formatId)) {
      setFormatId(platform.formats[0]?.id ?? "");
    }
  }, [platform, format, formatId]);

  const accept = useMemo(() => {
    if (!format) return IMAGE_MIME_TYPE;
    if (format.media_type === "video") return VIDEO;
    if (format.media_type === "image_or_video") return [...IMAGE_MIME_TYPE, ...VIDEO];
    return IMAGE_MIME_TYPE;
  }, [format]);

  function payload() {
    return {
      client_id: clientId,
      platform_id: platformId,
      format_id: format?.id,
      title: title.trim(),
      caption: caption.trim() || null,
      copy_text: copy.trim() || null,
      hashtags: format?.allows_hashtags ? hashtags.trim() || null : null,
      scheduled_date: date || null,
      scheduled_time: time || null,
      internal_description: internalDescription.trim() || null,
      waiting_note: waitingNote.trim() || null,
      internal_notes: notes.trim() || null,
    };
  }

  async function persist() {
    const body = JSON.stringify(payload());
    if (!clientId || !platformId || !format || !title.trim()) {
      throw new Error("Selecione cliente, plataforma, formato e título.");
    }
    if (contentId) return api<Content>(`/api/contents/${contentId}`, { method: "PATCH", body });
    return api<Content>("/api/contents", { method: "POST", body });
  }

  async function pushFiles(id: string, files: PendingFile[]) {
    let latest: Content | null = null;
    for (const item of files) {
      setProgress(0);
      latest = (await uploadWithProgress(`/api/contents/${id}/media`, item.file, setProgress)) as Content;
    }
    setProgress(null);
    files.forEach((item) => URL.revokeObjectURL(item.url));
    setPending([]);
    if (latest) setMedia(latest.media);
    return latest;
  }

  async function save(mode: "draft" | "progress" | "send") {
    if (mode === "progress" && waitingNote.trim().length < 3) {
      fail(new Error("Descreva o que está aguardando do cliente."));
      return;
    }
    setBusy(true);
    try {
      const saved = await persist();
      const uploaded = pending.length ? await pushFiles(saved.id, pending) : null;
      const current = uploaded ?? saved;
      if (mode === "progress") {
        await api(`/api/contents/${current.id}/hold`, {
          method: "POST",
          body: JSON.stringify({ waiting_note: waitingNote.trim() }),
        });
        ok("Conteúdo em andamento. O cliente já pode ver a observação.");
      } else if (mode === "send") {
        const path = current.status === "draft" || current.status === "in_progress" ? "submit" : "resubmit";
        const submitted = await api<Content>(`/api/contents/${current.id}/${path}`, { method: "POST" });
        ok(submitted.status === "resubmitted" ? "Conteúdo reenviado para aprovação." : "Conteúdo enviado para aprovação.");
      } else {
        ok("Rascunho salvo.");
      }
      router.push(`/admin/contents/${current.id}`);
      router.refresh();
    } catch (error) {
      fail(error);
      if (contentId) {
        const fresh = await api<Content>(`/api/contents/${contentId}`).catch(() => null);
        if (fresh) setMedia(fresh.media);
      }
    } finally {
      setBusy(false);
      setProgress(null);
    }
  }

  async function removeMedia(id: string) {
    if (!contentId) return;
    try {
      const updated = await api<Content>(`/api/contents/${contentId}/media/${id}`, { method: "DELETE" });
      setMedia(updated.media);
    } catch (error) {
      fail(error);
    }
  }

  async function move(id: string, direction: -1 | 1) {
    if (!contentId) return;
    const ids = media.map((item) => item.id);
    const index = ids.indexOf(id);
    const next = index + direction;
    if (index < 0 || next < 0 || next >= ids.length) return;
    [ids[index], ids[next]] = [ids[next], ids[index]];
    try {
      const updated = await api<Content>(`/api/contents/${contentId}/media/order`, {
        method: "PUT",
        body: JSON.stringify({ ids }),
      });
      setMedia(updated.media);
    } catch (error) {
      fail(error);
    }
  }

  const stories = format?.slug === "stories";

  return (
    <Stack gap="lg">
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <Select
          label="Cliente"
          placeholder="Selecione"
          data={clients.map((item) => ({ value: item.id, label: item.company_name }))}
          value={clientId || null}
          onChange={(value) => setClientId(value || "")}
          searchable
          required
        />
        <TextInput label="Título" value={title} onChange={(event) => setTitle(event.currentTarget.value)} required />
      </SimpleGrid>
      <div>
        <Text size="sm" fw={500} mb={6}>
          Plataforma
        </Text>
        <Group gap="xs">
          {platforms.map((item) => (
            <Button key={item.id} variant={item.id === platformId ? "filled" : "default"} onClick={() => setPlatformId(item.id)}>
              {item.name}
            </Button>
          ))}
        </Group>
      </div>
      <div>
        <Text size="sm" fw={500} mb={6}>
          Formato
        </Text>
        <Group gap="xs">
          {platform?.formats.map((item) => (
            <Button key={item.id} variant={item.id === format?.id ? "filled" : "default"} onClick={() => setFormatId(item.id)}>
              {item.name}
            </Button>
          ))}
        </Group>
      </div>
      <Textarea
        label={stories ? "Texto ou legenda" : "Legenda"}
        minRows={3}
        value={caption}
        onChange={(event) => setCaption(event.currentTarget.value)}
      />
      <Textarea label="Copy" minRows={4} value={copy} onChange={(event) => setCopy(event.currentTarget.value)} />
      {format?.allows_hashtags ? (
        <Textarea label="Hashtags" minRows={2} value={hashtags} onChange={(event) => setHashtags(event.currentTarget.value)} placeholder="#marca #campanha" />
      ) : (
        <Text size="sm" c="dimmed">
          Instagram não usa hashtags neste fluxo. O campo fica oculto de propósito.
        </Text>
      )}
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <TextInput type="date" label="Data programada" value={date} onChange={(event) => setDate(event.currentTarget.value)} />
        <TextInput type="time" label="Horário (opcional)" value={time} onChange={(event) => setTime(event.currentTarget.value)} />
      </SimpleGrid>
      <Stack gap="xs">
        <Text fw={600}>Arquivos</Text>
        <Text size="sm" c="dimmed">
          {format?.media_type === "multi_image"
            ? `Carrossel: de ${format.min_files} a ${format.max_files} imagens, na ordem de publicação.`
            : format?.media_type === "video"
              ? "Um vídeo MP4 ou MOV, com pré-visualização."
              : format?.media_type === "image_or_video"
                ? "Uma imagem ou um vídeo."
                : "Uma imagem JPG, PNG ou WEBP."}
        </Text>
        <Dropzone
          onDrop={(files) => {
            if (contentId) {
              setBusy(true);
              void (async () => {
                try {
                  const queued = files.map((file) => ({ key: crypto.randomUUID(), file, url: URL.createObjectURL(file) }));
                  await pushFiles(contentId, queued);
                  ok("Arquivo enviado.");
                } catch (error) {
                  fail(error);
                } finally {
                  setBusy(false);
                }
              })();
              return;
            }
            setPending((current) => [
              ...current,
              ...files.map((file) => ({ key: crypto.randomUUID(), file, url: URL.createObjectURL(file) })),
            ]);
          }}
          accept={accept}
          maxSize={format?.media_type === "video" || format?.media_type === "image_or_video" ? 200 * 1024 * 1024 : 15 * 1024 * 1024}
        >
          <Text ta="center" c="dimmed">
            Arraste os arquivos ou clique para selecionar
          </Text>
        </Dropzone>
        {progress !== null ? <Progress value={progress} color="brand" radius="xl" /> : null}
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          {media.map((item, index) => (
            <MediaCard
              key={item.id}
              url={item.url}
              name={item.filename}
              mime={item.mime_type}
              onRemove={() => void removeMedia(item.id)}
              onUp={index > 0 ? () => void move(item.id, -1) : undefined}
              onDown={index < media.length - 1 ? () => void move(item.id, 1) : undefined}
            />
          ))}
          {pending.map((item) => (
            <MediaCard
              key={item.key}
              url={item.url}
              name={item.file.name}
              mime={item.file.type}
              onRemove={() => setPending((current) => current.filter((file) => file.key !== item.key))}
            />
          ))}
        </SimpleGrid>
      </Stack>
      <Textarea
        label="Observação para o cliente"
        description="Aparece no portal quando o conteúdo fica em andamento. Ex.: aguardando o envio dos vídeos."
        minRows={3}
        value={waitingNote}
        onChange={(event) => setWaitingNote(event.currentTarget.value)}
      />
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <Textarea label="Descrição interna" value={internalDescription} onChange={(event) => setInternalDescription(event.currentTarget.value)} />
        <Textarea label="Observações internas" value={notes} onChange={(event) => setNotes(event.currentTarget.value)} />
      </SimpleGrid>
      <Group>
        <Button variant="default" loading={busy} onClick={() => void save("draft")}>
          {initial?.status === "in_progress" ? "Salvar alterações" : "Salvar rascunho"}
        </Button>
        {!initial || initial.status === "draft" || initial.status === "in_progress" ? (
          <Button variant="light" loading={busy} onClick={() => void save("progress")}>
            Salvar em andamento
          </Button>
        ) : null}
        <Button loading={busy} onClick={() => void save("send")}>
          {initial && initial.status !== "draft" && initial.status !== "in_progress" ? "Reenviar para aprovação" : "Enviar para aprovação"}
        </Button>
      </Group>
    </Stack>
  );
}

function MediaCard({
  url,
  name,
  mime,
  onRemove,
  onUp,
  onDown,
}: {
  url: string | null;
  name: string;
  mime: string;
  onRemove: () => void;
  onUp?: () => void;
  onDown?: () => void;
}) {
  return (
    <div style={{ border: "1px solid #eceaf2", borderRadius: 16, overflow: "hidden", background: "#fff" }}>
      {mime.startsWith("video/") ? (
        <video src={url ?? undefined} controls style={{ width: "100%", maxHeight: 220, background: "#111" }} />
      ) : (
        <img src={url ?? ""} alt={name} style={{ width: "100%", height: 180, objectFit: "cover" }} />
      )}
      <Group justify="space-between" p="xs">
        <Text size="xs" lineClamp={1}>
          {name}
        </Text>
        <Group gap={4}>
          {onUp ? (
            <Button size="compact-xs" variant="subtle" onClick={onUp}>
              Subir
            </Button>
          ) : null}
          {onDown ? (
            <Button size="compact-xs" variant="subtle" onClick={onDown}>
              Descer
            </Button>
          ) : null}
          <Button size="compact-xs" color="red" variant="subtle" onClick={onRemove}>
            Remover
          </Button>
        </Group>
      </Group>
    </div>
  );
}
