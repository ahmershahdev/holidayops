import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type Schemas, unwrap } from "../api/client";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async (): Promise<Schemas["User"] | null> => {
      try {
        return await unwrap(api.GET("/api/v1/auth/me/"));
      } catch (error) {
        if (error instanceof ApiError && error.status === 403) return null;
        throw error;
      }
    },
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
