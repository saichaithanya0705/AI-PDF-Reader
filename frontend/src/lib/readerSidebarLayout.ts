export const GOLDEN_RATIO = 1.618;

export type SidebarSplitFocus = 'chat-primary' | 'studio-primary';
export type StudioToolTab = 'insights' | 'audio';

export interface SidebarGridLayout {
  isOpen: boolean;
  isSplit: boolean;
  gridTemplateRows: string;
  upperSharePercent: number;
  lowerSharePercent: number;
}

/**
 * Computes golden-ratio (1 : 1.618) CSS Grid row tracks for the reader's right
 * sidebar hosting upper studio tools (Insights / Audio) and lower Assistant Chat.
 */
export function getReaderSidebarLayout(
  hasUpperPane: boolean,
  hasLowerPane: boolean,
  focus: SidebarSplitFocus = 'chat-primary'
): SidebarGridLayout {
  if (hasUpperPane && hasLowerPane) {
    return focus === 'studio-primary'
      ? {
          isOpen: true,
          isSplit: true,
          gridTemplateRows: '1.618fr auto 1fr',
          upperSharePercent: 61.8,
          lowerSharePercent: 38.2,
        }
      : {
          isOpen: true,
          isSplit: true,
          gridTemplateRows: '1fr auto 1.618fr',
          upperSharePercent: 38.2,
          lowerSharePercent: 61.8,
        };
  }

  if (hasUpperPane) {
    return {
      isOpen: true,
      isSplit: false,
      gridTemplateRows: '1fr',
      upperSharePercent: 100,
      lowerSharePercent: 0,
    };
  }

  if (hasLowerPane) {
    return {
      isOpen: true,
      isSplit: false,
      gridTemplateRows: '1fr',
      upperSharePercent: 0,
      lowerSharePercent: 100,
    };
  }

  return {
    isOpen: false,
    isSplit: false,
    gridTemplateRows: 'none',
    upperSharePercent: 0,
    lowerSharePercent: 0,
  };
}
