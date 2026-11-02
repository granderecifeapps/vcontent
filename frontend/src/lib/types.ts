export type Role = "admin" | "client";

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  phone: string | null;
  is_active: boolean;
  unread_count?: number;
  client?: { id: string; company_name: string; status: string } | null;
};

export type Page<T> = { items: T[]; total: number; page: number; page_size: number };

export type ClientAccess = {
  user_id: string;
  email: string;
  full_name: string;
  is_active: boolean;
};

export type Client = {
  id: string;
  company_name: string;
  contact_name: string;
  email: string;
  phone: string | null;
  logo_url: string | null;
  description: string | null;
  internal_notes?: string | null;
  status: "active" | "inactive";
  created_at: string;
  updated_at: string;
  access?: ClientAccess | null;
  contract?: { filename: string | null; url: string | null; uploaded_at: string | null } | null;
  stats?: Record<string, number>;
  content_total?: number;
};

export type FormatInfo = {
  id: string;
  slug: string;
  name: string;
  media_type: "single_image" | "multi_image" | "video" | "image_or_video";
  allows_hashtags: boolean;
  min_files: number;
  max_files: number;
};

export type Platform = { id: string; slug: string; name: string; formats: FormatInfo[] };

export type Media = {
  id: string;
  url: string | null;
  filename: string;
  mime_type: string;
  size_bytes: number;
  sort_order: number;
};

export type Content = {
  id: string;
  client_id: string;
  client_name: string | null;
  platform: { id: string; slug: string; name: string };
  format: FormatInfo;
  title: string;
  internal_description?: string | null;
  scheduled_date: string | null;
  scheduled_time: string | null;
  caption: string | null;
  copy_text: string | null;
  hashtags: string | null;
  waiting_note: string | null;
  status: string;
  internal_notes?: string | null;
  version: number;
  latest_reason: string | null;
  media: Media[];
  created_by_name: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
};

export type HistoryEvent = {
  id: string;
  kind: string;
  content_id: string;
  content_title: string | null;
  action: string;
  reason: string | null;
  actor_name: string;
  version: number | null;
  created_at: string;
};

export type Notice = {
  id: string;
  type: string;
  title: string;
  body: string;
  data: { content_id?: string };
  read_at: string | null;
  created_at: string;
};
