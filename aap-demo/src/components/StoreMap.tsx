import React from 'react';
import {useCurrentFrame, interpolate, Easing} from 'remotion';
import {colors} from '../styles/tokens';

interface StoreMapProps {
  revealStartFrame?: number;
  revealDuration?: number;
}

export const StoreMap: React.FC<StoreMapProps> = ({
  revealStartFrame = 0,
  revealDuration = 90,
}) => {
  const frame = useCurrentFrame();

  const rows = 6;
  const cols = 9;
  const spacingX = 180;
  const spacingY = 130;
  const offsetX = 120;
  const offsetY = 140;

  const nodes: {x: number; y: number; delay: number}[] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const jitterX = Math.sin(r * 7 + c * 3) * 15;
      const jitterY = Math.cos(r * 5 + c * 11) * 10;
      nodes.push({
        x: offsetX + c * spacingX + jitterX,
        y: offsetY + r * spacingY + jitterY,
        delay: (r + c) * 2,
      });
    }
  }

  return (
    <svg
      width={1920}
      height={1080}
      viewBox="0 0 1920 1080"
      style={{position: 'absolute', top: 0, left: 0}}
    >
      {/* Connecting lines */}
      {nodes.map((node, i) => {
        const rightNeighbor = i % cols < cols - 1 ? nodes[i + 1] : null;
        const bottomNeighbor = i + cols < nodes.length ? nodes[i + cols] : null;
        const lineOpacity = interpolate(
          frame,
          [revealStartFrame + node.delay, revealStartFrame + node.delay + 15],
          [0, 0.15],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
        );

        return (
          <React.Fragment key={`lines-${i}`}>
            {rightNeighbor && (
              <line
                x1={node.x} y1={node.y}
                x2={rightNeighbor.x} y2={rightNeighbor.y}
                stroke={colors.coolGray}
                strokeWidth={2}
                opacity={lineOpacity}
              />
            )}
            {bottomNeighbor && (
              <line
                x1={node.x} y1={node.y}
                x2={bottomNeighbor.x} y2={bottomNeighbor.y}
                stroke={colors.coolGray}
                strokeWidth={2}
                opacity={lineOpacity}
              />
            )}
          </React.Fragment>
        );
      })}

      {/* Nodes (stores) */}
      {nodes.map((node, i) => {
        const nodeOpacity = interpolate(
          frame,
          [revealStartFrame + node.delay, revealStartFrame + node.delay + 10],
          [0, 1],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
        );
        const nodeScale = interpolate(
          frame,
          [revealStartFrame + node.delay, revealStartFrame + node.delay + 10],
          [0.3, 1],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)},
        );

        return (
          <circle
            key={`node-${i}`}
            cx={node.x}
            cy={node.y}
            r={4 * nodeScale}
            fill={colors.yellow}
            opacity={nodeOpacity}
          />
        );
      })}
    </svg>
  );
};
