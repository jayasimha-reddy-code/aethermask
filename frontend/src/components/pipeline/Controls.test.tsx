import { DropZone, PassphraseField, ProfilePicker, NumericModeToggle } from './Controls';

describe('Controls component', () => {
  test('exports DropZone, PassphraseField, ProfilePicker, and NumericModeToggle', () => {
    expect(typeof DropZone).toBe('function');
    expect(typeof PassphraseField).toBe('function');
    expect(typeof ProfilePicker).toBe('function');
    expect(typeof NumericModeToggle).toBe('function');
  });
});
