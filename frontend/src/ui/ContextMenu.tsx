import React, { useEffect, useState } from 'react';
import type { DropdownItem } from './Dropdown';

type ContextMenuProps = {
  items: DropdownItem[];
  children: React.ReactNode;
  className?: string;
};

export function ContextMenu({ items, children, className }: ContextMenuProps) {
  const [position, setPosition] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (!position) return;

    const close = () => setPosition(null);
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        close();
      }
    };

    document.addEventListener('pointerdown', close);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', close);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [position]);

  return (
    <div
      className={['ds-context-menu', className].filter(Boolean).join(' ')}
      onContextMenu={(event) => {
        event.preventDefault();
        setPosition({ x: event.clientX, y: event.clientY });
      }}
    >
      {children}
      {position ? (
        <div
          className="ds-menu"
          role="menu"
          style={{ left: position.x, top: position.y }}
          onPointerDown={(event) => event.stopPropagation()}
        >
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              className="ds-menu-item"
              role="menuitem"
              disabled={item.disabled}
              onClick={() => {
                item.onSelect?.();
                setPosition(null);
              }}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export default ContextMenu;
