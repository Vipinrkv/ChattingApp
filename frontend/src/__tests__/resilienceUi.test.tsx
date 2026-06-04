import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

const useOfflineStatusMock = vi.fn();
const flushQueuedRequestsMock = vi.fn();
const apiRequestMock = vi.fn();

vi.mock('../hooks/useOfflineStatus', () => ({
  useOfflineStatus: () => useOfflineStatusMock(),
}));

vi.mock('../lib/offlineQueue', () => ({
  flushQueuedRequests: (...args: unknown[]) => flushQueuedRequestsMock(...args),
}));

vi.mock('../lib/api', () => ({
  apiRequest: (...args: unknown[]) => apiRequestMock(...args),
}));

import OfflineStatus from '../components/OfflineStatus';
import ReconnectBanner from '../components/ReconnectBanner';
import RetryPanel from '../components/RetryPanel';
import { ToastProvider } from '../ui/ToastProvider';

describe('resilience UI states', () => {
  beforeEach(() => {
    useOfflineStatusMock.mockReset();
    flushQueuedRequestsMock.mockReset();
    apiRequestMock.mockReset();
  });

  it('shows offline mode with queued actions', () => {
    useOfflineStatusMock.mockReturnValue({ isOnline: false, queuedCount: 2 });

    render(
      <ToastProvider>
        <OfflineStatus />
      </ToastProvider>,
    );

    expect(screen.getByText('Offline mode')).toBeInTheDocument();
    expect(screen.getByText('Offline mode active. Recent pages and queued actions remain available.')).toBeInTheDocument();
  });

  it('flushes queued offline actions when the app returns online', async () => {
    useOfflineStatusMock.mockReturnValue({ isOnline: true, queuedCount: 1 });
    flushQueuedRequestsMock.mockResolvedValue({ flushed: 1, remaining: 0, failed: 0 });

    render(
      <ToastProvider>
        <OfflineStatus />
      </ToastProvider>,
    );

    await waitFor(() => expect(flushQueuedRequestsMock).toHaveBeenCalled());
    expect(await screen.findByText('1 offline action synced.')).toBeInTheDocument();
  });

  it('renders retry panels for backend unavailable states', () => {
    const onRetry = vi.fn();

    render(
      <RetryPanel
        title="Admin console unavailable"
        message="Could not reach the backend."
        onRetry={onRetry}
      />,
    );

    expect(screen.getByRole('alert')).toHaveTextContent('Admin console unavailable');
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('renders reconnect banners for websocket recovery', () => {
    const { rerender } = render(
      <ReconnectBanner isConnecting isConnected={false} label="Direct chat" />,
    );

    expect(screen.getByText('Direct chat reconnecting…')).toBeInTheDocument();

    rerender(<ReconnectBanner isConnecting={false} isConnected={false} label="Direct chat" />);
    expect(screen.getByText('Direct chat offline. New messages may sync after reconnect.')).toBeInTheDocument();

    rerender(<ReconnectBanner isConnecting={false} isConnected={false} error="socket failed" label="Direct chat" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Direct chat unavailable');
  });
});
