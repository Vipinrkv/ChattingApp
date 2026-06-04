import React from 'react';

export const Avatar: React.FC<{ src?: string; alt?: string; size?: number }> = React.memo(({ src, alt = 'avatar', size = 40 }) => {
  const sizeClass = size === 80 ? 'avatar avatar-lg' : 'avatar';
  return <img src={src} alt={alt} className={sizeClass} loading="lazy" />;
});

export default Avatar;
