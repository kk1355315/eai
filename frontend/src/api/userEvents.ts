import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./client";
import type { UserFoodEvent, UserFoodEventCreate, UserFoodHabit } from "./types";

export const habitsQueryKey = ["habits"] as const;

export async function createUserFoodEvent(
  payload: UserFoodEventCreate,
): Promise<UserFoodEvent> {
  return apiRequest<UserFoodEvent>("/user-food-events", {
    method: "POST",
    body: {
      quantity: 1,
      metadata: {},
      ...payload,
    },
  });
}

export async function fetchHabits(): Promise<UserFoodHabit[]> {
  return apiRequest<UserFoodHabit[]>("/habits");
}

export function useHabits() {
  return useQuery({
    queryKey: habitsQueryKey,
    queryFn: fetchHabits,
  });
}

export function useCreateUserFoodEvent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createUserFoodEvent,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["inventory"] });
      void queryClient.invalidateQueries({ queryKey: ["advice"] });
      void queryClient.invalidateQueries({ queryKey: habitsQueryKey });
    },
  });
}
