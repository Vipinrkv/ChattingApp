import React, { useId, useState } from 'react';

type TooltipProps = {
  content: React.ReactNode;
  children: React.ReactNode;
  className?: string;
};

export function Tooltip({ content, children, className }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const id = useId();

  return (
    <span
      className={['ds-tooltip', className].filter(Boolean).join(' ')}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
      aria-describedby={visible ? id : undefined}
    >
      {children}
      {visible ? (
        <span id={id} role="tooltip" className="ds-tooltip-bubble">
          {content}
        </span>
      ) : null}
    </span>
  );
}

export default Tooltip;
