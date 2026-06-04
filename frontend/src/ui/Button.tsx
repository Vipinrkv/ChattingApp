import React from 'react';

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'ghost';
};

export const Button: React.FC<ButtonProps> = ({ variant = 'primary', children, className, ...rest }) => {
  const base = 'btn';
  const vclass = variant === 'primary' ? '' : 'btn-ghost';
  return (
    <button className={[base, vclass, className].filter(Boolean).join(' ')} {...rest}>
      {children}
    </button>
  );
};

export default Button;
