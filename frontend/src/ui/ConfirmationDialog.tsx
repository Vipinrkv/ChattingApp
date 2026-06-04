import Modal from './Modal';

interface ConfirmationDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export default function ConfirmationDialog({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  loading = false,
}: ConfirmationDialogProps) {
  return (
    <Modal title={title} isOpen={isOpen} onClose={onCancel} footer={
      <div className="dialog-actions">
        <button className="secondary-button" type="button" onClick={onCancel} disabled={loading}>
          {cancelLabel}
        </button>
        <button className="primary-button" type="button" onClick={onConfirm} disabled={loading}>
          {loading ? 'Working...' : confirmLabel}
        </button>
      </div>
    }>
      <p>{message}</p>
    </Modal>
  );
}
