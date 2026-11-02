"use client";

import { Center, Loader } from "@mantine/core";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

export default function HomePage() {
  const { user, ready } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!ready) return;
    router.replace(!user ? "/login" : user.role === "admin" ? "/admin" : "/portal");
  }, [ready, user, router]);
  return (
    <Center h="100vh">
      <Loader color="brand" />
    </Center>
  );
}
