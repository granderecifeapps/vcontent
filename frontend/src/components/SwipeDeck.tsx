"use client";

import { Button, Group, Modal, Stack, Text, Textarea, Title } from "@mantine/core";
import { animate, motion, useDragControls, useMotionValue, useTransform } from "framer-motion";
import { useState } from "react";
import { scheduleLabel } from "@/lib/labels";
import { fail } from "@/lib/feedback";
import { StatusBadge } from "./StatusBadge";
import type { Content } from "@/lib/types";

export function SwipeDeck({
  items,
  onApprove,
  onChanges,
}: {
  items: Content[];
  onApprove: (item: Content) => Promise<void>;
  onChanges: (item: Content, reason: string) => Promise<void>;
}) {
  const [reasonOpen, setReasonOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [slide, setSlide] = useState(0);
  const current = items[0];
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-220, 220], [-12, 12]);
  const approveOpacity = useTransform(x, [30, 140], [0, 1]);
  const changeOpacity = useTransform(x, [-140, -30], [1, 0]);
  const controls = useDragControls();

  if (!current) {
    return (
      <Stack align="center" gap="xs" py={80}>
        <Title order={3}>Tudo em dia</Title>
        <Text c="dimmed">Não há conteúdos aguardando a sua aprovação.</Text>
      </Stack>
    );
  }

  async function approve() {
    if (!current || busy) return;
    setBusy(true);
    try {
      await animate(x, 460, { duration: 0.22 });
      await onApprove(current);
      x.set(0);
      setSlide(0);
    } catch (error) {
      fail(error);
      x.set(0);
    } finally {
      setBusy(false);
    }
  }

  function askChanges() {
    if (busy) return;
    setReason("");
    setReasonOpen(true);
    void animate(x, 0, { type: "spring", stiffness: 320, damping: 28 });
  }

  return (
    <div className="swipe-stage">
      {items[1] ? (
        <div style={{ position: "absolute", inset: 18, borderRadius: 28, background: "#fff", border: "1px solid #eceaf2", transform: "scale(0.96) translateY(10px)" }} />
      ) : null}
      <motion.article
        key={current.id}
        drag="x"
        dragControls={controls}
        dragListener={false}
        dragConstraints={{ left: 0, right: 0 }}
        dragElastic={0.9}
        style={{ x, rotate, position: "absolute", inset: 0, borderRadius: 28, background: "#fff", border: "1px solid #eceaf2", boxShadow: "0 20px 50px rgba(17,17,20,0.08)", overflow: "hidden", display: "flex", flexDirection: "column" }}
        onDragEnd={(_, info) => {
          if (info.offset.x > 110 || info.velocity.x > 700) void approve();
          else if (info.offset.x < -110 || info.velocity.x < -700) askChanges();
        }}
      >
        <div style={{ position: "relative", flex: 1, minHeight: 240, background: "#111114" }} onPointerDown={(event) => controls.start(event)}>
          <motion.div style={{ opacity: approveOpacity, position: "absolute", top: 16, left: 16, zIndex: 2, background: "#16794c", color: "#fff", borderRadius: 999, padding: "6px 12px", fontWeight: 700 }}>
            Aprovar
          </motion.div>
          <motion.div style={{ opacity: changeOpacity, position: "absolute", top: 16, right: 16, zIndex: 2, background: "#c92a2a", color: "#fff", borderRadius: 999, padding: "6px 12px", fontWeight: 700 }}>
            Ajustes
          </motion.div>
          <Preview item={current} slide={slide} setSlide={setSlide} />
        </div>
        <Stack gap={6} p="md" onPointerDown={(event) => controls.start(event)}>
          <Group justify="space-between">
            <Text size="sm" c="dimmed">
              {current.platform.name} · {current.format.name}
            </Text>
            <StatusBadge status={current.status} />
          </Group>
          <Title order={3}>{current.title}</Title>
          <Text size="sm">{scheduleLabel(current.scheduled_date, current.scheduled_time)}</Text>
          {current.caption ? <Text size="sm" lineClamp={3}>{current.caption}</Text> : null}
          {current.copy_text ? <Text size="sm" c="dimmed" lineClamp={3}>{current.copy_text}</Text> : null}
          {current.hashtags ? <Text size="sm" c="brand">{current.hashtags}</Text> : null}
          <Text size="xs" c="dimmed">
            {items.length} na fila · arraste para a direita para aprovar ou para a esquerda para pedir ajuste
          </Text>
        </Stack>
      </motion.article>
      <Group grow mt="md" style={{ position: "absolute", left: 0, right: 0, bottom: -64 }}>
        <Button size="lg" color="red" variant="light" disabled={busy} onClick={askChanges}>
          Solicitar ajustes
        </Button>
        <Button size="lg" color="teal" disabled={busy} onClick={() => void approve()}>
          Aprovar
        </Button>
      </Group>
      <Modal opened={reasonOpen} onClose={() => setReasonOpen(false)} title="O que precisa mudar?">
        <Stack>
          <Text size="sm" c="dimmed">
            O motivo é obrigatório e fica registrado no histórico.
          </Text>
          <Textarea minRows={4} value={reason} onChange={(event) => setReason(event.currentTarget.value)} placeholder="Descreva o ajuste" />
          <Button
            loading={busy}
            disabled={reason.trim().length < 3}
            onClick={() => {
              if (!current) return;
              setBusy(true);
              void onChanges(current, reason.trim())
                .then(() => setReasonOpen(false))
                .finally(() => setBusy(false));
            }}
          >
            Enviar solicitação
          </Button>
        </Stack>
      </Modal>
    </div>
  );
}

function Preview({ item, slide, setSlide }: { item: Content; slide: number; setSlide: (value: number) => void }) {
  const media = item.media[slide] ?? item.media[0];
  if (!media?.url) {
    return <Group h="100%" justify="center"><Text c="white">Sem mídia</Text></Group>;
  }
  return (
    <div style={{ height: "100%", position: "relative" }}>
      {media.mime_type.startsWith("video/") ? (
        <video data-nodrag src={media.url} controls playsInline style={{ width: "100%", height: "100%", objectFit: "contain", background: "#111" }} onPointerDown={(event) => event.stopPropagation()} />
      ) : (
        <img src={media.url} alt={item.title} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      )}
      {item.media.length > 1 ? (
        <Group justify="space-between" style={{ position: "absolute", left: 8, right: 8, bottom: 8 }} onPointerDown={(event) => event.stopPropagation()}>
          <Button size="xs" variant="white" disabled={slide === 0} onClick={() => setSlide(Math.max(0, slide - 1))}>
            Anterior
          </Button>
          <Text c="white" size="xs">
            {slide + 1}/{item.media.length}
          </Text>
          <Button size="xs" variant="white" disabled={slide >= item.media.length - 1} onClick={() => setSlide(Math.min(item.media.length - 1, slide + 1))}>
            Próxima
          </Button>
        </Group>
      ) : null}
    </div>
  );
}
