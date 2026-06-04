import React from 'react';

export const Input: React.FC<React.InputHTMLAttributes<HTMLInputElement>> = ({ className, ...rest }) => {
  return <input className={["input", className].filter(Boolean).join(' ')} {...rest} />;
};

export default Input;
