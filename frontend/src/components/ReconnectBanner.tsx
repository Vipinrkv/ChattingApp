type ReconnectBannerProps = {
  isConnecting: boolean;
  isConnected: boolean;
  error?: string | null;
  label?: string;
};

function ReconnectBanner({ isConnecting, isConnected, error, label = 'Realtime connection' }: ReconnectBannerProps) {
  if (error) {
    return (
      <div className="reconnect-banner error" role="alert">
        {label} unavailable. Retrying when the network recovers.
      </div>
    );
  }

  if (isConnecting) {
    return (
      <div className="reconnect-banner" role="status" aria-live="polite">
        {label} reconnecting…
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="reconnect-banner warn" role="status" aria-live="polite">
        {label} offline. New messages may sync after reconnect.
      </div>
    );
  }

  return null;
}

export default ReconnectBanner;
