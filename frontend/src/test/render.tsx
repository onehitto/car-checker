import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router";

import { createQueryClient } from "@/app/queryClient";
import { ToastProvider } from "@/components/ui";

/** Render inside the app providers (query cache, toasts, router). */
export function renderWithProviders(ui: ReactElement, { route = "/" } = {}) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}
