import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import { type ReactElement, type ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { LanguageProvider, type Language } from "../lib/language";

type RenderWithProvidersOptions = RenderOptions & {
  language?: Language;
  route?: string;
};

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

export function renderWithProviders(
  ui: ReactElement,
  { language = "en", route = "/", ...options }: RenderWithProvidersOptions = {},
) {
  const queryClient = createTestQueryClient();

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <LanguageProvider initialLanguage={language}>
          <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
        </LanguageProvider>
      </QueryClientProvider>
    );
  }

  return {
    queryClient,
    ...render(ui, { wrapper: Wrapper, ...options }),
  };
}
