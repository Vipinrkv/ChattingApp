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
  listRef?: React.Ref<any>;
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
  listRef,
}: VirtualizedListProps<T>) {
  const localRef = useRef<any>(null);
  const activeRef = (listRef as React.MutableRefObject<any>) || localRef;

  const Row = ({ index, style }: ListChildComponentProps) =>
    React.createElement('div', { style }, renderItem(items[index], index));

  useEffect(() => {
    if (activeRef.current && typeof itemHeight === 'function') {
      activeRef.current.resetAfterIndex(0, true);
    }
  }, [items, itemHeight, activeRef]);

  if (typeof itemHeight === 'function') {
    return (
      <div className={className}>
        <VariableList
          ref={activeRef}
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
        ref={activeRef}
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
