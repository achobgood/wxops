import React from 'react';
import {useCurrentFrame, interpolate, Easing} from 'remotion';
import {evolvePath} from '@remotion/paths';
import {colors} from '../styles/tokens';

const ROAD_PATH =
  'M -50,580 C 300,580 450,420 700,420 S 1100,580 1400,480 S 1700,380 1970,440';

interface HighwayProps {
  drawStartFrame?: number;
  drawDuration?: number;
  progress?: number;
}

export const Highway: React.FC<HighwayProps> = ({
  drawStartFrame = 0,
  drawDuration = 45,
  progress: progressOverride,
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
      {/* Road edge lines */}
      <path
        d={ROAD_PATH}
        fill="none"
        stroke={colors.coolGray}
        strokeWidth={50}
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
        strokeWidth={48}
        strokeLinecap="round"
        strokeDasharray={roadEvolve.strokeDasharray}
        strokeDashoffset={roadEvolve.strokeDashoffset}
      />
      {/* Center dashed line — yellow accent */}
      <path
        d={ROAD_PATH}
        fill="none"
        stroke={colors.yellow}
        strokeWidth={3}
        strokeLinecap="round"
        strokeDasharray="16 12"
        strokeDashoffset={dashEvolve.strokeDashoffset}
        opacity={progress}
      />
    </svg>
  );
};

export {ROAD_PATH};
