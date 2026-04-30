import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {backgroundStyle, colors, fonts, fadeUp} from '../styles/tokens';
import {Highway} from '../components/Highway';
import {Car} from '../components/Car';
import {RoadSign} from '../components/RoadSign';

export const TheCall: React.FC = () => {
  const frame = useCurrentFrame();

  const titleAnim = fadeUp(frame, 30, 40, 25);

  return (
    <AbsoluteFill style={backgroundStyle}>
      {/* Highway draws itself */}
      <Highway drawStartFrame={5} drawDuration={50} />

      {/* Car enters and drives to ~40% of the path */}
      <Car enterFrame={20} startDistance={0} endDistance={40} travelDuration={80} />

      {/* Road signs along the highway */}
      <RoadSign label="PSTN" x={180} y={520} enterFrame={25} />
      <RoadSign label="WxCC Entry Point" x={380} y={360} enterFrame={35} />
      <RoadSign label="IVR Flow" x={600} y={360} enterFrame={45} />

      {/* Title */}
      <div
        style={{
          position: 'absolute',
          bottom: 120,
          left: 0,
          right: 0,
          textAlign: 'center',
          opacity: titleAnim.opacity,
          transform: titleAnim.transform,
        }}
      >
        <h1
          style={{
            fontFamily: fonts.headline,
            fontSize: 64,
            fontWeight: 700,
            color: colors.white,
            margin: 0,
            textTransform: 'uppercase',
            letterSpacing: '-0.02em',
          }}
        >
          Intelligent Call Routing
        </h1>
        <div style={{width: 80, height: 3, backgroundColor: colors.yellow, margin: '12px auto 0'}} />
        <p
          style={{
            fontFamily: fonts.body,
            fontSize: 22,
            color: colors.coolGray,
            margin: '12px 0 0',
          }}
        >
          Advance Auto Parts — 35,000 phones across 4,500 stores
        </p>
      </div>
    </AbsoluteFill>
  );
};
