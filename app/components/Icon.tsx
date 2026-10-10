// Stroke icons drawn from the design canvas (24 px grid, round caps). Decorative: hidden from screen readers.
import Svg, { Circle, Path, Rect } from 'react-native-svg';

const PATHS = {
  mic: ['M5 11a7 7 0 0 0 14 0', 'M12 18v3'],
  back: ['M19 12H5', 'M11 6l-6 6 6 6'],
  check: ['M5 12.5l4.5 4.5L19 7.5'],
  alert: ['M12 5v9', 'M12 19v.5'],
  x: ['M7 7l10 10', 'M17 7L7 17'],
  dash: ['M6 12h12'],
  history: ['M3 12a9 9 0 1 0 3-6.7', 'M3 4v5h5'],
  clock: ['M12 7v5l3 2'],
  speaker: ['M4 9v6h4l5 4V5L8 9H4z', 'M16.5 8.5a5 5 0 0 1 0 7'],
  globe: ['M3 12h18', 'M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18'],
  chevron: ['M9 6l6 6-6 6'],
  home: ['M3 11l9-7 9 7', 'M5 10v10h14V10'],
  truck: ['M3 7h11v9H3z', 'M14 10h4l3 3v3h-7'],
  chart: ['M4 20V10', 'M10 20V4', 'M16 20v-7', 'M22 20H2'],
  warning: ['M12 3l9.5 17h-19L12 3z', 'M12 10v4', 'M12 17.5v.5'],
  pin: ['M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z'],
  plus: ['M12 5v14', 'M5 12h14'],
  basket: ['M3 9h18l-2 11H5L3 9z', 'M8 9l4-6 4 6'],
  settings: ['M4 6h9', 'M17 6h3', 'M4 12h3', 'M11 12h9', 'M4 18h11', 'M19 18h1'],
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 20, color, strokeWidth = 2 }: { name: IconName; size?: number; color: string; strokeWidth?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth}
      strokeLinecap="round" strokeLinejoin="round" accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      {name === 'mic' && <Rect x={9} y={3} width={6} height={11} rx={3} />}
      {(name === 'globe' || name === 'clock') && <Circle cx={12} cy={12} r={9} />}
      {name === 'pin' && <Circle cx={12} cy={10} r={2.5} />}
      {name === 'settings' && (
        <>
          <Circle cx={15} cy={6} r={2} />
          <Circle cx={9} cy={12} r={2} />
          <Circle cx={17} cy={18} r={2} />
        </>
      )}
      {name === 'truck' && (
        <>
          <Circle cx={7} cy={18} r={2} />
          <Circle cx={17} cy={18} r={2} />
        </>
      )}
      {PATHS[name].map((d) => (
        <Path key={d} d={d} />
      ))}
    </Svg>
  );
}
