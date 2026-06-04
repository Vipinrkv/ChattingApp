import { useEffect, useRef } from 'react';

export function useRenderCount(name = 'component') {
  const renderCount = useRef(0);
  renderCount.current += 1;

  useEffect(() => {
    if (import.meta.env.DEV) {
      console.debug(`[render] ${name}:`, renderCount.current);
    }
  });

  return renderCount.current;
}
