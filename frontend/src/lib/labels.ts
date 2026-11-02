export const STATUS: Record<string, { label: string; color: string }> = {
  draft: { label: "Rascunho", color: "gray" },
  in_progress: { label: "Em andamento", color: "orange" },
  pending_approval: { label: "Aguardando aprovação", color: "yellow" },
  approved: { label: "Aprovado", color: "green" },
  changes_requested: { label: "Ajustes solicitados", color: "red" },
  in_review: { label: "Em revisão", color: "orange" },
  resubmitted: { label: "Reenviado", color: "blue" },
  published: { label: "Publicado", color: "teal" },
  cancelled: { label: "Cancelado", color: "gray" },
};

export const ACTIONS: Record<string, string> = {
  created: "Conteúdo criado",
  held: "Marcado como em andamento",
  waiting_updated: "Observação atualizada",
  submitted: "Enviado para aprovação",
  approved: "Aprovado",
  changes_requested: "Ajustes solicitados",
  review_started: "Revisão iniciada",
  resubmitted: "Reenviado para aprovação",
  published: "Marcado como publicado",
  cancelled: "Cancelado",
  deleted: "Excluído",
  comment: "Comentário",
};

export function statusLabel(status: string) {
  return STATUS[status]?.label ?? status;
}

export function formatDate(value?: string | null) {
  if (!value) return "Sem data";
  const [date] = value.split("T");
  const [year, month, day] = date.split("-");
  if (!year || !month || !day) return value;
  return `${day}/${month}/${year}`;
}

export function formatWhen(value?: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return formatDate(value);
  return date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

export function scheduleLabel(date?: string | null, time?: string | null) {
  if (!date) return "Sem data programada";
  return time ? `${formatDate(date)} às ${time}` : formatDate(date);
}
