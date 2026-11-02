"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { apiFetch } from "@/lib/api";
import type { AuthStatus } from "@/lib/types";

export function useAuthGuard() {
  const router = useRouter();
  const query = useQuery({
    queryKey: ["auth-status"],
    queryFn: () => apiFetch<AuthStatus>("/auth/status"),
    retry: false,
  });

  useEffect(() => {
    if (query.error) router.replace("/login");
  }, [query.error, router]);

  return query;
}
