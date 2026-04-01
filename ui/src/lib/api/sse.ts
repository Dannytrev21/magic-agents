type EventSourceCtor = new (url: string, eventSourceInitDict?: EventSourceInit) => EventSource;

type EventStreamOptions = {
  EventSourceImpl?: EventSourceCtor;
};

type EventListenerFn = (event: Event) => void;

export function createEventStream(
  url: string,
  { EventSourceImpl = EventSource }: EventStreamOptions = {},
) {
  const eventSource = new EventSourceImpl(url);

  return {
    eventSource,
    subscribe(type: string, listener: EventListenerFn) {
      eventSource.addEventListener(type, listener);
    },
    close() {
      eventSource.close();
    },
  };
}
