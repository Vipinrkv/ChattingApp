import { ReactNode } from 'react';

interface ModalProps {
  title?: string;
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}

export default function Modal({ title, isOpen, onClose, children, footer }: ModalProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true">
      <div className="modal-card glass-panel">
        <div className="modal-header">
          {title ? <h3>{title}</h3> : null}
          <button className="modal-close" type="button" onClick={onClose} aria-label="Close dialog">
            x
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer ? <div className="modal-footer">{footer}</div> : null}
      </div>
    </div>
  );
}
