import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {backgroundStyle, colors, fonts, fadeUp} from '../styles/tokens';
import {Highway} from '../components/Highway';
import {Car} from '../components/Car';
import {RoadSign} from '../components/RoadSign';
import {POSScreen} from '../components/POSScreen';

export const TheStore: React.FC = () => {
  const frame = useCurrentFrame();

  const storeLabel = fadeUp(frame, 20, 20, 15);

  return (
    <AbsoluteFill style={backgroundStyle}>
      {/* Highway fully drawn */}
      <Highway progress={1} />

      {/* Car drives from ~40% to ~60% and stops */}
      <Car
        enterFrame={0}
        startDistance={40}
        endDistance={58}
        travelDuration={40}
      />

      {/* Road sign: Bridged Transfer */}
      <RoadSign label="Bridged Transfer" x={850} y={360} enterFrame={15} variant="emphasis" />

      {/* Store label */}
      <div
        style={{
          position: 'absolute',
          left: 900,
          top: 500,
          opacity: storeLabel.opacity,
          transform: storeLabel.transform,
        }}
      >
        <div
          style={{
            fontFamily: fonts.headline,
            fontSize: 32,
            fontWeight: 700,
            color: colors.white,
            textTransform: 'uppercase',
            letterSpacing: '0.02em',
          }}
        >
          Store #247
        </div>
        <div
          style={{
            fontFamily: fonts.body,
            fontSize: 16,
            color: colors.coolGray,
            marginTop: 4,
          }}
        >
          Associate answers — webhook fires
        </div>
      </div>

      {/* POS Screen Pop slides in */}
      <POSScreen
        customerName="John Smith"
        loyaltyTier="Gold — 12,400 pts"
        recentOrder="Duralast Gold DG1625 Brake Pads"
        vehicle="2019 Honda Civic EX"
        enterFrame={25}
        x={1350}
        y={200}
      />
    </AbsoluteFill>
  );
};
