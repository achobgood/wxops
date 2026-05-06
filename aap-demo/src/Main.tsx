import React from 'react';
import {AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {acts, FPS, TOTAL_FRAMES} from './styles/tokens';
import {ColdOpen} from './scenes/ColdOpen';
import {TheRouting} from './scenes/TheRouting';
import {TheStore} from './scenes/TheStore';
import {TheTransition} from './scenes/TheTransition';
import {TheCountdown} from './scenes/TheCountdown';
import {TheSnap} from './scenes/TheSnap';
import {TheCatch} from './scenes/TheCatch';
import {TheScale} from './scenes/TheScale';
import {ProgressBar} from './components/ProgressBar';

const DIALOGUE = [
  {file: 's1-customer-brakepads.mp3', from: 60, dur: 91, vol: 1.0},
  {file: 's2-narrator-routing.mp3', from: 270, dur: 306, vol: 1.0},
  {file: 's3-narrator-webhook.mp3', from: 630, dur: 223, vol: 1.0},
  {file: 's3-associate-greeting.mp3', from: 860, dur: 131, vol: 1.0},
  {file: 's3-customer-duralast.mp3', from: 930, dur: 93, vol: 1.0},
  {file: 's3-associate-hold.mp3', from: 1020, dur: 73, vol: 1.0},
  {file: 's4-customer-sure.mp3', from: 1080, dur: 30, vol: 1.0},
  {file: 's4-narrator-webhook.mp3', from: 1110, dur: 153, vol: 1.0},
  {file: 's5-narrator-fifteen.mp3', from: 1650, dur: 43, vol: 1.0},
  {file: 's5-narrator-thirty.mp3', from: 2100, dur: 29, vol: 1.0},
  {file: 's5-narrator-counting.mp3', from: 2160, dur: 35, vol: 0.9},
  {file: 's6-narrator-disconnected.mp3', from: 2310, dur: 126, vol: 1.0},
  {file: 's7-ai-greeting.mp3', from: 2430, dur: 221, vol: 1.0},
  {file: 's7-customer-great.mp3', from: 2660, dur: 46, vol: 1.0},
  {file: 's7-ai-availability.mp3', from: 2720, dur: 222, vol: 1.0},
  {file: 's8-narrator-onecall.mp3', from: 3050, dur: 66, vol: 1.0},
  {file: 's8-narrator-everywhere.mp3', from: 3130, dur: 138, vol: 1.0},
  {file: 's8-narrator-everytime.mp3', from: 3350, dur: 112, vol: 0.95},
] as const;

function scoreVolume(f: number): number {
  const SILENCE_START = acts.theSnap.from + 15;
  const SILENCE_END = SILENCE_START + 15;

  if (f >= SILENCE_START && f <= SILENCE_END) return 0;

  const fadeIn = interpolate(f, [acts.theRouting.from, acts.theRouting.from + FPS], [0, 0.18], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const tensionBuild = interpolate(
    f,
    [acts.theCountdown.from, acts.theSnap.from],
    [0.18, 0.25],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const resolution = interpolate(
    f,
    [acts.theCatch.from, acts.theCatch.from + 30],
    [0.12, 0.20],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const fadeOut = interpolate(f, [TOTAL_FRAMES - FPS * 3, TOTAL_FRAMES], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  let vol = 0;
  if (f < acts.theRouting.from) vol = 0;
  else if (f < acts.theCountdown.from) vol = fadeIn;
  else if (f < acts.theSnap.from) vol = tensionBuild;
  else if (f < acts.theCatch.from) vol = 0.12;
  else vol = resolution;

  return vol * fadeOut;
}

const SceneSequence: React.FC<{
  from: number;
  duration: number;
  name: string;
  fadeIn?: number;
  fadeOut?: number;
  children: React.ReactNode;
}> = ({from, duration, name, fadeIn: fi = 15, fadeOut: fo = 15, children}) => {
  const frame = useCurrentFrame();
  const inOpacity = (from === 0 || fi === 0) ? 1 : interpolate(frame, [from, from + fi], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const outOpacity = fo === 0 ? 1 : interpolate(frame, [from + duration - fo, from + duration], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <Sequence from={from} durationInFrames={duration} name={name}>
      <AbsoluteFill style={{opacity: Math.min(inOpacity, outOpacity)}}>
        {children}
      </AbsoluteFill>
    </Sequence>
  );
};

export const Main: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: '#000'}}>
    {/* Continuous score */}
    <Audio
      volume={scoreVolume}
      src={staticFile('audio/score.mp3')}
    />

    {/* Dialogue lines */}
    {DIALOGUE.map((d) => (
      <Sequence key={d.file} from={d.from} durationInFrames={d.dur} name={`Dialogue: ${d.file}`}>
        <Audio
          volume={(f) =>
            d.vol * interpolate(f, [0, 5], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
          }
          src={staticFile(`audio/dialogue/${d.file}`)}
        />
      </Sequence>
    ))}

    {/* SFX */}
    <Sequence from={30} durationInFrames={100} name="SFX: Phone Ring">
      <Audio volume={0.2} src={staticFile('audio/sfx/phone-ringing.mp3')} />
    </Sequence>
    <Sequence from={630} durationInFrames={40} name="SFX: Notification Chime">
      <Audio volume={0.25} src={staticFile('audio/sfx/notification-chime.mp3')} />
    </Sequence>
    <Sequence from={1095} durationInFrames={20} name="SFX: Hold Click">
      <Audio volume={0.3} src={staticFile('audio/sfx/hold-click.mp3')} />
    </Sequence>
    <Sequence from={1220} durationInFrames={1030} name="SFX: Clock Ticking">
      <Audio
        volume={(f) => interpolate(f, [0, 1030], [0.1, 0.3], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        })}
        src={staticFile('audio/sfx/clock-ticking.mp3')}
      />
    </Sequence>
    <Sequence from={2255} durationInFrames={40} name="SFX: Electrical Crackle">
      <Audio volume={0.4} src={staticFile('audio/sfx/electrical-crackle.mp3')} />
    </Sequence>
    <Sequence from={2420} durationInFrames={40} name="SFX: AI Connect Chime">
      <Audio volume={0.25} src={staticFile('audio/sfx/ai-connect-chime.mp3')} />
    </Sequence>
    <Sequence from={3500} durationInFrames={60} name="SFX: Complete Chime">
      <Audio volume={0.2} src={staticFile('audio/sfx/complete-chime.mp3')} />
    </Sequence>

    {/* Visual scenes */}
    <SceneSequence from={acts.coldOpen.from} duration={acts.coldOpen.duration} name="Sc 1 — Cold Open" fadeIn={0} fadeOut={15}>
      <ColdOpen />
    </SceneSequence>
    <SceneSequence from={acts.theRouting.from} duration={acts.theRouting.duration} name="Sc 2 — The Routing" fadeIn={15} fadeOut={20}>
      <TheRouting />
    </SceneSequence>
    <SceneSequence from={acts.theStore.from} duration={acts.theStore.duration} name="Sc 3 — The Store" fadeIn={15} fadeOut={15}>
      <TheStore />
    </SceneSequence>
    <SceneSequence from={acts.theTransition.from} duration={acts.theTransition.duration} name="Sc 4 — The Transition" fadeIn={15} fadeOut={0}>
      <TheTransition />
    </SceneSequence>
    <SceneSequence from={acts.theCountdown.from} duration={acts.theCountdown.duration} name="Sc 5 — The Countdown" fadeIn={0} fadeOut={0}>
      <TheCountdown />
    </SceneSequence>
    <SceneSequence from={acts.theSnap.from} duration={acts.theSnap.duration} name="Sc 6 — The Snap" fadeIn={0} fadeOut={20}>
      <TheSnap />
    </SceneSequence>
    <SceneSequence from={acts.theCatch.from} duration={acts.theCatch.duration} name="Sc 7 — The Catch" fadeIn={20} fadeOut={30}>
      <TheCatch />
    </SceneSequence>
    <SceneSequence from={acts.theScale.from} duration={acts.theScale.duration} name="Sc 8 — The Scale" fadeIn={30} fadeOut={0}>
      <TheScale />
    </SceneSequence>

    {/* Global progress bar */}
    <ProgressBar />
  </AbsoluteFill>
);
