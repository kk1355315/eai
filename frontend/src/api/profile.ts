import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./client";
import type { Profile, ProfilePatch } from "./types";
import { filterSupportedFoodLabels } from "../lib/foods";

export const profileQueryKey = ["profile"] as const;

export async function fetchProfile(): Promise<Profile> {
  const profile = await apiRequest<Profile>("/profile");
  return {
    ...profile,
    avoid_foods: filterSupportedFoodLabels(profile.avoid_foods),
  };
}

export async function patchProfile(patch: ProfilePatch): Promise<Profile> {
  return apiRequest<Profile>("/profile", {
    method: "PATCH",
    body: {
      ...patch,
      avoid_foods: patch.avoid_foods
        ? filterSupportedFoodLabels(patch.avoid_foods)
        : patch.avoid_foods,
    },
  });
}

export function useProfile() {
  return useQuery({
    queryKey: profileQueryKey,
    queryFn: fetchProfile,
  });
}

export function usePatchProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: patchProfile,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: profileQueryKey });
      void queryClient.invalidateQueries({ queryKey: ["advice"] });
    },
  });
}
