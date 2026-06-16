import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./client";
import type {
  ConfirmChangeRequest,
  InventoryItem,
  InventoryPatch,
} from "./types";
import { filterSupportedInventory } from "../lib/mappers";

export const inventoryQueryKey = ["inventory"] as const;
export const storageStatesQueryKey = ["inventory", "storage-states"] as const;

export async function fetchInventory(): Promise<InventoryItem[]> {
  const items = await apiRequest<InventoryItem[]>("/inventory");
  return filterSupportedInventory(items);
}

export async function fetchStorageStates(): Promise<InventoryItem[]> {
  const items = await apiRequest<InventoryItem[]>("/inventory/storage-states");
  return filterSupportedInventory(items);
}

export async function patchInventoryItem(
  itemId: number,
  patch: InventoryPatch,
): Promise<InventoryItem> {
  return apiRequest<InventoryItem>(`/inventory/${itemId}`, {
    method: "PATCH",
    body: patch,
  });
}

export async function confirmInventoryChange(
  itemId: number,
  payload: ConfirmChangeRequest,
): Promise<InventoryItem> {
  return apiRequest<InventoryItem>(`/inventory/${itemId}/confirm-change`, {
    method: "POST",
    body: payload,
  });
}

export function useInventory() {
  return useQuery({
    queryKey: inventoryQueryKey,
    queryFn: fetchInventory,
  });
}

export function useStorageStates() {
  return useQuery({
    queryKey: storageStatesQueryKey,
    queryFn: fetchStorageStates,
  });
}

export function usePatchInventory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      itemId,
      patch,
    }: {
      itemId: number;
      patch: InventoryPatch;
    }) => patchInventoryItem(itemId, patch),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: inventoryQueryKey });
      void queryClient.invalidateQueries({ queryKey: storageStatesQueryKey });
      void queryClient.invalidateQueries({ queryKey: ["advice"] });
    },
  });
}

export function useConfirmInventoryChange() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      itemId,
      payload,
    }: {
      itemId: number;
      payload: ConfirmChangeRequest;
    }) => confirmInventoryChange(itemId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: inventoryQueryKey });
      void queryClient.invalidateQueries({ queryKey: storageStatesQueryKey });
      void queryClient.invalidateQueries({ queryKey: ["advice"] });
      void queryClient.invalidateQueries({ queryKey: ["habits"] });
    },
  });
}
