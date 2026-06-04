import React from 'react';

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  tone?: 'neutral' | 'success' | 'danger' | 'warning';
};

export function Badge({ tone = 'neutral', className, children, ...rest }: BadgeProps) {
  return (
    <span className={['ds-badge', className].filter(Boolean).join(' ')} data-tone={tone} {...rest}>
      {children}
    </span>
  );
}

export default Badge;
