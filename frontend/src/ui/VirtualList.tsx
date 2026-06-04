import React, { useCallback, useEffect, useRef, useState } from 'react';

type VirtualListProps<T> = {
  items: T[];
  itemHeight: number; // estimated fixed height per item
  overscan?: number;
  className?: string;
  renderItem: (item: T, index: number) => React.ReactNode;
};

export function VirtualList<T>({ items, itemHeight, overscan = 5, className, renderItem }: VirtualListProps<T>) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const paddingRef = useRef<HTMLDivElement | null>(null);
  const [scrollTop, setScrollTop] = useState(0);

  const onScroll = useCallback(() => {
    if (!containerRef.current) return;
    setScrollTop(containerRef.current.scrollTop);
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, [onScroll]);

  const containerHeight = containerRef.current?.clientHeight ?? 600;
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const visibleCount = Math.ceil(containerHeight / itemHeight) + overscan * 2;
  const endIndex = Math.min(items.length, startIndex + visibleCount);

  const topPadding = startIndex * itemHeight;
  const bottomPadding = Math.max(0, (items.length - endIndex) * itemHeight);

  useEffect(() => {
    if (!paddingRef.current) return;
    paddingRef.current.style.paddingTop = `${topPadding}px`;
    paddingRef.current.style.paddingBottom = `${bottomPadding}px`;
  }, [topPadding, bottomPadding]);

  return (
    <div ref={containerRef} className={`virtual-scroll-container ${className ?? ''}`}>
      <div ref={paddingRef} className="virtual-list-padding">
        {items.slice(startIndex, endIndex).map((item, i) => renderItem(item, startIndex + i))}
      </div>
    </div>
  );
}

export default VirtualList;
