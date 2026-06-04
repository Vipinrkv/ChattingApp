import React, { useMemo, useState } from 'react';

export type TabItem = {
  id: string;
  label: React.ReactNode;
  content: React.ReactNode;
  disabled?: boolean;
};

type TabsProps = {
  items: TabItem[];
  defaultValue?: string;
  value?: string;
  onChange?: (id: string) => void;
  className?: string;
  ariaLabel?: string;
};

export function Tabs({ items, defaultValue, value, onChange, className, ariaLabel = 'Tabs' }: TabsProps) {
  const firstEnabled = items.find((item) => !item.disabled)?.id;
  const [internalValue, setInternalValue] = useState(defaultValue ?? firstEnabled);
  const selectedValue = value ?? internalValue;
  const selectedItem = useMemo(
    () => items.find((item) => item.id === selectedValue) ?? items.find((item) => !item.disabled),
    [items, selectedValue],
  );

  const selectTab = (id: string) => {
    setInternalValue(id);
    onChange?.(id);
  };

  return (
    <div className={['ds-tabs', className].filter(Boolean).join(' ')}>
      <div className="ds-tab-list" role="tablist" aria-label={ariaLabel}>
        {items.map((item) => (
          <button
            key={item.id}
            id={`tab-${item.id}`}
            type="button"
            className="ds-tab"
            role="tab"
            aria-selected={selectedItem?.id === item.id}
            aria-controls={`tabpanel-${item.id}`}
            disabled={item.disabled}
            onClick={() => selectTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {selectedItem ? (
        <div
          id={`tabpanel-${selectedItem.id}`}
          className="ds-tab-panel"
          role="tabpanel"
          aria-labelledby={`tab-${selectedItem.id}`}
        >
          {selectedItem.content}
        </div>
      ) : null}
    </div>
  );
}

export default Tabs;
