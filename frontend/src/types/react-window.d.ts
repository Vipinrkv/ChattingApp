declare module 'react-window' {
  import type { ComponentType, CSSProperties } from 'react';

  export interface ListChildComponentProps {
    index: number;
    style: CSSProperties;
    data?: unknown;
  }

  export const FixedSizeList: ComponentType<any>;
  export const VariableSizeList: ComponentType<any>;
}
