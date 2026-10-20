import { Composition } from "remotion";
import { Demo, TOTAL_FRAMES, VIDEO_FPS } from "./Demo";

export const Root = () => <Composition id="Demo" component={Demo} durationInFrames={TOTAL_FRAMES} fps={VIDEO_FPS} width={1920} height={1080} />;
