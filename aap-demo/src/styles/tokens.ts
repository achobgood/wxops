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
} as const;

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;
export const TOTAL_FRAMES = 2700;

export const chapters = {
  theCall: {from: 0, duration: 600},
  theStore: {from: 600, duration: 450},
  theHold: {from: 1050, duration: 600},
  theRecall: {from: 1650, duration: 600},
  theScale: {from: 2250, duration: 450},
} as const;

export const backgroundStyle: React.CSSProperties = {
  backgroundColor: colors.black,
};

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
