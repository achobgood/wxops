import {loadFont as loadBarlowCondensed} from '@remotion/google-fonts/BarlowCondensed';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {loadFont as loadIBMPlexMono} from '@remotion/google-fonts/IBMPlexMono';
import {interpolate, Easing} from 'remotion';

const {fontFamily: barlowCondensed} = loadBarlowCondensed();
const {fontFamily: inter} = loadInter();
const {fontFamily: ibmPlexMono} = loadIBMPlexMono();

export const fonts = {
  headline: barlowCondensed,
  body: inter,
  mono: ibmPlexMono,
} as const;

export const colors = {
  black: '#000000',
  yellow: '#FFCF06',
  white: '#FFFFFF',
  coolGray: '#9CA3AF',
  darkGray: '#1A1A1A',
  amber: '#F59E0B',
  gold: '#D4A843',
  red: '#FF4444',
  orange: '#FF8C00',
} as const;

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;
export const TOTAL_FRAMES = 3600;

export const acts = {
  coldOpen:      {from: 0,    duration: 240},
  theRouting:    {from: 240,  duration: 360},
  theStore:      {from: 600,  duration: 480},
  theTransition: {from: 1080, duration: 120},
  theCountdown:  {from: 1200, duration: 1050},
  theSnap:       {from: 2250, duration: 150},
  theCatch:      {from: 2400, duration: 600},
  theScale:      {from: 3000, duration: 600},
} as const;

export const backgroundStyle: React.CSSProperties = {
  backgroundColor: colors.black,
  background: 'linear-gradient(180deg, #0a0e1a 0%, #000000 60%)',
};

export function desaturate(
  frame: number,
  startFrame: number,
  endFrame: number,
): string {
  const gray = interpolate(frame, [startFrame, endFrame], [0, 100], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return `grayscale(${gray}%)`;
}

export function pulseGlow(
  frame: number,
  startFrame: number,
  speed = 1,
): number {
  const t = (frame - startFrame) * speed;
  return 0.5 + 0.5 * Math.sin(t * 0.3);
}

export function fadeUp(
  frame: number,
  startFrame: number,
  distance = 30,
  duration = 20,
): {opacity: number; transform: string} {
  const opacity = interpolate(frame, [startFrame, startFrame + duration], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const y = interpolate(frame, [startFrame, startFrame + duration], [distance, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  return {opacity, transform: `translateY(${y}px)`};
}

export function fadeIn(
  frame: number,
  startFrame: number,
  duration = 15,
): number {
  return interpolate(frame, [startFrame, startFrame + duration], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
}

export function colorTransition(
  frame: number,
  triggerFrame: number,
  fromColor: string,
  toColor: string,
  duration = 20,
): string {
  const t = interpolate(frame, [triggerFrame, triggerFrame + duration], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return t < 0.5 ? fromColor : toColor;
}
