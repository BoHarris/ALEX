import React from "react";
import AnimatedLoginSVG from "../components/animatedHeading";
import PiiSentinelUI from "../components/PiiSentinelUI";

import { SUPPORTED_EXTENSIONS } from "../utils/constants";
function Home() {
  return (
    <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center text-white">
      <AnimatedLoginSVG />
      <p className="mt-6 text-center text-gray-400 max-w-md">
        ALEX is your privacy-sidekick, helping you detect and redact PII while
        enhancing data protection. Navigate to your dashboard to get started.
      </p>
      <PiiSentinelUI allowedTypes={SUPPORTED_EXTENSIONS} />
    </div>
  );
}

export default Home;
