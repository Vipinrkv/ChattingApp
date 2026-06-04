import { useCallback, useState } from 'react';

export function useModal<T = undefined>(initialIsOpen = false) {
  const [isOpen, setIsOpen] = useState(initialIsOpen);
  const [payload, setPayload] = useState<T | null>(null);

  const open = useCallback((value?: T) => {
    setPayload(value ?? null);
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    setPayload(null);
  }, []);

  return { isOpen, payload, open, close };
}
