import type { ReactNode } from 'react';

type RetryPanelProps = {
  title: string;
  message: string;
  actionLabel?: string;
  onRetry?: () => void;
  children?: ReactNode;
};

function RetryPanel({ title, message, actionLabel = 'Retry', onRetry, children }: RetryPanelProps) {
  return (
    <div className="fallback-panel" role="alert">
      <div>
        <p className="fallback-kicker">System fallback</p>
        <h2>{title}</h2>
        <p>{message}</p>
      </div>
      {children}
      {onRetry ? (
        <button className="primary-button fallback-action" type="button" onClick={onRetry}>
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}

export default RetryPanel;
