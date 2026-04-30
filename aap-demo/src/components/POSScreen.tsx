import React from 'react';
import {useCurrentFrame, interpolate, Easing} from 'remotion';
import {colors, fonts} from '../styles/tokens';

interface POSScreenProps {
  customerName: string;
  loyaltyTier: string;
  recentOrder: string;
  vehicle: string;
  enterFrame?: number;
  x?: number;
  y?: number;
}

export const POSScreen: React.FC<POSScreenProps> = ({
  customerName,
  loyaltyTier,
  recentOrder,
  vehicle,
  enterFrame = 0,
  x = 1350,
  y = 200,
}) => {
  const frame = useCurrentFrame();

  const slideX = interpolate(
    frame,
    [enterFrame, enterFrame + 25],
    [120, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)},
  );
  const opacity = interpolate(
    frame,
    [enterFrame, enterFrame + 15],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const rows = [
    {label: 'Customer', value: customerName},
    {label: 'Loyalty', value: loyaltyTier},
    {label: 'Recent Order', value: recentOrder},
    {label: 'Vehicle', value: vehicle},
  ];

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: 420,
        opacity,
        transform: `translateX(${slideX}px)`,
      }}
    >
      {/* Header */}
      <div
        style={{
          borderBottom: `2px solid ${colors.yellow}`,
          paddingBottom: 8,
          marginBottom: 16,
        }}
      >
        <div
          style={{
            fontFamily: fonts.headline,
            fontSize: 22,
            fontWeight: 700,
            color: colors.yellow,
            textTransform: 'uppercase',
            letterSpacing: '0.03em',
          }}
        >
          POS Screen Pop
        </div>
        <div
          style={{
            fontFamily: fonts.body,
            fontSize: 13,
            color: colors.coolGray,
            marginTop: 2,
          }}
        >
          Store #247 — Register R3
        </div>
      </div>
      {/* Data rows */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
          padding: '16px 20px',
          border: `1px solid ${colors.coolGray}`,
          borderRadius: 8,
          backgroundColor: colors.darkGray,
        }}
      >
        {rows.map((row, i) => {
          const rowOpacity = interpolate(
            frame,
            [enterFrame + 15 + i * 5, enterFrame + 25 + i * 5],
            [0, 1],
            {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
          );
          return (
            <div key={row.label} style={{display: 'flex', justifyContent: 'space-between', opacity: rowOpacity}}>
              <span style={{fontFamily: fonts.body, fontSize: 15, color: colors.coolGray, fontWeight: 600}}>
                {row.label}
              </span>
              <span style={{fontFamily: fonts.body, fontSize: 15, color: colors.white}}>
                {row.value}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
