import { useCallback, useState } from 'react';

export function useLoadingError() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async <T>(promise: Promise<T>): Promise<T> => {
    setLoading(true);
    setError(null);

    try {
      return await promise;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An unexpected error occurred';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setLoading(false);
    setError(null);
  }, []);

  return {
    loading,
    error,
    run,
    reset,
    setError,
    setLoading,
  };
}
