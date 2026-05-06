import {TextToSpeechClient} from '@google-cloud/text-to-speech';
import {writeFile, mkdir} from 'fs/promises';
import {join, dirname} from 'path';
import {fileURLToPath} from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUTPUT_DIR = join(__dirname, '..', 'public', 'audio', 'dialogue');

const VOICES = {
  narrator: 'en-US-Chirp3-HD-Alnilam',
  customer: 'en-US-Chirp3-HD-Achernar',
  associate: 'en-US-Chirp3-HD-Sadachbia',
  aiAgent: 'en-US-Chirp3-HD-Leda',
};

const LINES = [
  // Scene 1: Cold Open
  {id: 's1-customer-brakepads', voice: 'customer', text: 'Yeah, I need the ceramic brake pads for my Civic.', rate: 1.0},

  // Scene 2: The Routing
  {id: 's2-narrator-routing', voice: 'narrator', text: 'Every call enters through Webex Contact Center. The IVR identifies the customer in milliseconds — name, loyalty tier, order history — before the call ever reaches the store.', rate: 1.02},

  // Scene 3: The Store
  {id: 's3-narrator-webhook', voice: 'narrator', text: "When the associate answers, a webhook fires. In under a second, the customer's full profile appears on the POS screen.", rate: 1.02},
  {id: 's3-associate-greeting', voice: 'associate', text: "Thanks for calling Advance Auto, this is Mike. I see you're looking at brake pads for your Civic?", rate: 1.0},
  {id: 's3-customer-duralast', voice: 'customer', text: "Yeah, the Duralast Gold set — do you have 'em in stock?", rate: 1.0},
  {id: 's3-associate-hold', voice: 'associate', text: 'Let me check on that. Mind if I put you on hold for just a sec?', rate: 1.0},

  // Scene 4: The Transition
  {id: 's4-customer-sure', voice: 'customer', text: 'Sure, no problem.', rate: 1.0},
  {id: 's4-narrator-webhook', voice: 'narrator', text: 'But a webhook is already watching. The moment the hold begins, a sixty-second countdown starts.', rate: 1.02},

  // Scene 5: The Countdown
  {id: 's5-narrator-fifteen', voice: 'narrator', text: 'Fifteen seconds.', rate: 0.95},
  {id: 's5-narrator-thirty', voice: 'narrator', text: 'Thirty seconds.', rate: 0.95},
  {id: 's5-narrator-counting', voice: 'narrator', text: 'The webhook is counting.', rate: 0.9},

  // Scene 6: The Snap
  {id: 's6-narrator-disconnected', voice: 'narrator', text: "The associate is disconnected. But the call doesn't drop.", rate: 0.95},

  // Scene 7: The Catch
  {id: 's7-ai-greeting', voice: 'aiAgent', text: 'Hi John, I see you were waiting at Store 247. I can help with those ceramic brake pads for your 2019 Civic.', rate: 1.0},
  {id: 's7-customer-great', voice: 'customer', text: "Oh — yeah, that'd be great.", rate: 1.0},
  {id: 's7-ai-availability', voice: 'aiAgent', text: "I'm showing the Duralast Gold set in stock at Store 312, eight minutes from you. Would you like me to put one on hold?", rate: 1.0},

  // Scene 8: The Scale
  {id: 's8-narrator-onecall', voice: 'narrator', text: 'That was one call. One store.', rate: 0.95},
  {id: 's8-narrator-everywhere', voice: 'narrator', text: 'But this runs everywhere — thirty-five thousand phones, forty-five hundred stores.', rate: 1.0},
  {id: 's8-narrator-everytime', voice: 'narrator', text: 'Every call. Every store. Every time.', rate: 0.9},
];

async function main() {
  if (!process.env.GOOGLE_CLOUD_TTS_CREDENTIALS) {
    console.error('Error: GOOGLE_CLOUD_TTS_CREDENTIALS environment variable not set.');
    process.exit(1);
  }

  const client = new TextToSpeechClient({
    credentials: JSON.parse(process.env.GOOGLE_CLOUD_TTS_CREDENTIALS),
  });

  await mkdir(OUTPUT_DIR, {recursive: true});

  for (const line of LINES) {
    const voiceName = VOICES[line.voice];
    console.log(`Generating: ${line.id} (${line.voice}: ${voiceName})...`);

    const [response] = await client.synthesizeSpeech({
      input: {text: line.text},
      voice: {languageCode: 'en-US', name: voiceName},
      audioConfig: {audioEncoding: 'MP3', speakingRate: line.rate},
    });

    const outputPath = join(OUTPUT_DIR, `${line.id}.mp3`);
    await writeFile(outputPath, Buffer.from(response.audioContent));
    console.log(`  → ${outputPath}`);
  }

  console.log(`\nDone! ${LINES.length} dialogue files generated.`);
}

main().catch((err) => {
  console.error('TTS generation failed:', err.message);
  process.exit(1);
});
