"use client";

import dayjs from "dayjs";
import "dayjs/locale/pt-br";

dayjs.locale("pt-br");

export function DatesReady({ children }: { children: React.ReactNode }) {
  return children;
}
