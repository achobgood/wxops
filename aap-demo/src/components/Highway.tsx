import React from 'react';
import {useCurrentFrame, interpolate, Easing} from 'remotion';
import {evolvePath} from '@remotion/paths';
import {colors} from '../styles/tokens';

const ROAD_PATH =
  'M -50,580 C 300,580 450,420 700,420 S 1100,580 1400,480 S 1700,380 1970,440';

const LAMP_POSITIONS = [0.1, 0.25, 0.4, 0.55, 0.7, 0.85];

interface HighwayProps {
  drawStartFrame?: number;
  drawDuration?: number;
  progress?: number;
  showLamps?: boolean;
  carProgress?: number;
}

export const Highway: React.FC<HighwayProps> = ({
  drawStartFrame = 0,
  drawDuration = 45,
  progress: progressOverride,
  showLamps = false,
  carProgress = 0,
}) => {
  const frame = useCurrentFrame();

  const progress =
    progressOverride ??
    interpolate(frame, [drawStartFrame, drawStartFrame + drawDuration], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    });

  const roadEvolve = evolvePath(progress, ROAD_PATH);
  const dashEvolve = evolvePath(progress, ROAD_PATH);

  return (
    <svg
      width={1920}
      height={1080}
      viewBox="0 0 1920 1080"
      style={{position: 'absolute', top: 0, left: 0}}
    >
      <defs>
        <filter id="road-glow">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <radialGradient id="lamp-glow">
          <stop offset="0%" stopColor={colors.yellow} stopOpacity="0.6" />
          <stop offset="100%" stopColor={colors.yellow} stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Wet road reflection (mirrored below, low opacity) */}
      <path
        d={ROAD_PATH}
        fill="none"
        stroke={colors.coolGray}
        strokeWidth={60}
        strokeLinecap="round"
        strokeDasharray={roadEvolve.strokeDasharray}
        strokeDashoffset={roadEvolve.strokeDashoffset}
        opacity={0.04}
        transform="translate(0, 30)"
      />

      {/* Road edge lines */}
      <path
        d={ROAD_PATH}
        fill="none"
        stroke={colors.coolGray}
        strokeWidth={90}
        strokeLinecap="round"
        strokeDasharray={roadEvolve.strokeDasharray}
        strokeDashoffset={roadEvolve.strokeDashoffset}
        opacity={0.15}
      />
      {/* Road surface */}
      <path
        d={ROAD_PATH}
        fill="none"
        stroke={colors.darkGray}
        strokeWidth={86}
        strokeLinecap="round"
        strokeDasharray={roadEvolve.strokeDasharray}
        strokeDashoffset={roadEvolve.strokeDashoffset}
      />
      {/* Center dashed line — yellow accent */}
      <path
        d={ROAD_PATH}
        fill="none"
        stroke={colors.yellow}
        strokeWidth={4}
        strokeLinecap="round"
        strokeDasharray="16 12"
        strokeDashoffset={dashEvolve.strokeDashoffset}
        opacity={progress}
        filter="url(#road-glow)"
      />

      {/* Street lamps */}
      {showLamps && LAMP_POSITIONS.map((pos, i) => {
        const lampLit = carProgress >= pos - 0.05;
        const glowOpacity = lampLit
          ? interpolate(carProgress, [pos - 0.05, pos + 0.05], [0, 0.8], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
          : 0;
        const x = interpolate(pos, [0, 1], [0, 1920]);
        const y = interpolate(pos, [0, 0.5, 1], [560, 400, 420]);
        return (
          <React.Fragment key={i}>
            <circle cx={x} cy={y - 60} r={40} fill="url(#lamp-glow)" opacity={glowOpacity} />
            <line x1={x} y1={y - 50} x2={x} y2={y - 20} stroke={colors.coolGray} strokeWidth={2} opacity={progress * 0.4} />
            <circle cx={x} cy={y - 52} r={3} fill={lampLit ? colors.yellow : colors.coolGray} opacity={progress * 0.8} />
          </React.Fragment>
        );
      })}
    </svg>
  );
};

export {ROAD_PATH};
