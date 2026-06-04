/* eslint-disable react/forbid-dom-props */
import React, { useEffect, useRef } from 'react';
import {
  FixedSizeList as FixedList,
  VariableSizeList as VariableList,
  ListChildComponentProps,
} from 'react-window';

export type VirtualizedListProps<T> = {
  items: T[];
  height: number;
  itemHeight: number | ((item: T, index: number) => number);
  estimatedItemHeight?: number;
  width?: number | string;
  overscan?: number;
  className?: string;
  renderItem: (item: T, index: number) => React.ReactNode;
};

export default function VirtualizedList<T>({
  items,
  height,
  itemHeight,
  estimatedItemHeight = 140,
  width = '100%',
  overscan = 3,
  className,
  renderItem,
}: VirtualizedListProps<T>) {
  const listRef = useRef<any>(null);

  const Row = ({ index, style }: ListChildComponentProps) =>
    React.createElement('div', { style }, renderItem(items[index], index));

  useEffect(() => {
    if (listRef.current && typeof itemHeight === 'function') {
      listRef.current.resetAfterIndex(0, true);
    }
  }, [items, itemHeight]);

  if (typeof itemHeight === 'function') {
    return (
      <div className={className}>
        <VariableList
          ref={listRef}
          height={height}
          itemCount={items.length}
          itemSize={(index: number) => itemHeight(items[index], index)}
          estimatedItemSize={estimatedItemHeight}
          width={width}
          overscanCount={overscan}
        >
          {Row}
        </VariableList>
      </div>
    );
  }

  return (
    <div className={className}>
      <FixedList
        height={height}
        itemCount={items.length}
        itemSize={itemHeight}
        width={width}
        overscanCount={overscan}
      >
        {Row}
      </FixedList>
    </div>
  );
}
