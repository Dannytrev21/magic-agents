import { type ReactNode, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { EventStoreProvider, createEventStore } from '@/lib/api/eventStore';

function createQueryClient() {
  const queryRetryCount = import.meta.env.MODE === 'test' ? 0 : 1;

  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: queryRetryCount,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient);
  const [eventStore] = useState(createEventStore);

  return (
    <QueryClientProvider client={queryClient}>
      <EventStoreProvider store={eventStore}>{children}</EventStoreProvider>
    </QueryClientProvider>
  );
}
