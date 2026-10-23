import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Schemas, unwrap } from "../api/client";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    // 204 when signed out.
    queryFn: async (): Promise<Schemas["User"] | null> =>
      (await unwrap(api.GET("/api/v1/auth/me/"))) ?? null,
    staleTime: 60_000,
  });
}

export function useEnsureCsrf() {
  return useQuery({
    queryKey: ["csrf"],
    queryFn: () => unwrap(api.GET("/api/v1/auth/csrf/")),
    staleTime: Infinity,
  });
}

export function useLogout() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/auth/logout/")),
    onSuccess: () => {
      client.clear();
    },
  });
}
