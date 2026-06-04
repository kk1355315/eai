import { useMutation, useQuery } from "@tanstack/react-query";
import { apiRequest } from "./client";
import type {
  EvidenceSearchResponse,
  LlmAdviceResponse,
  LlmGenerateRequest,
  ShoppingAdviceResponse,
  TodayAdviceResponse,
} from "./types";
import {
  filterSupportedAdviceItems,
  filterSupportedTodayAdvice,
} from "../lib/mappers";

export const todayAdviceQueryKey = ["advice", "today"] as const;
export const shoppingAdviceQueryKey = ["advice", "shopping"] as const;

export async function fetchTodayAdvice(): Promise<TodayAdviceResponse> {
  const advice = await apiRequest<TodayAdviceResponse>("/api/advice/today");
  return filterSupportedTodayAdvice(advice);
}

export async function fetchShoppingAdvice(): Promise<ShoppingAdviceResponse> {
  const advice = await apiRequest<ShoppingAdviceResponse>("/api/advice/shopping");
  return {
    ...advice,
    recommendations: filterSupportedAdviceItems(advice.recommendations),
  };
}

export async function generateLlmAdvice(
  payload: LlmGenerateRequest,
): Promise<LlmAdviceResponse> {
  const advice = await apiRequest<LlmAdviceResponse>("/api/advice/llm", {
    method: "POST",
    body: payload,
  });
  return {
    ...advice,
    advice: {
      ...advice.advice,
      recommendations: filterSupportedAdviceItems(advice.advice.recommendations),
    },
  };
}

export async function searchAdviceEvidence(
  query: string,
): Promise<EvidenceSearchResponse> {
  return apiRequest<EvidenceSearchResponse>("/api/advice/evidence-search", {
    query: { query },
  });
}

export function useTodayAdvice() {
  return useQuery({
    queryKey: todayAdviceQueryKey,
    queryFn: fetchTodayAdvice,
  });
}

export function useShoppingAdvice() {
  return useQuery({
    queryKey: shoppingAdviceQueryKey,
    queryFn: fetchShoppingAdvice,
  });
}

export function useGenerateLlmAdvice() {
  return useMutation({
    mutationFn: generateLlmAdvice,
  });
}
