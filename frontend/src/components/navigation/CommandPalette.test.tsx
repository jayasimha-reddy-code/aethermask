import { CommandPalette, useCommandPaletteHotkey } from './CommandPalette';

describe('CommandPalette component', () => {
  test('exports palette component and hotkey hook', () => {
    expect(typeof CommandPalette).toBe('function');
    expect(typeof useCommandPaletteHotkey).toBe('function');
  });
});
