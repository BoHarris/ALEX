import React from "react";
import PiiSentinelUI from "../components/PiiSentinelUI";

import { SUPPORTED_EXTENSIONS } from "../utils/constants";

function Upload() {
  const [supportedFileTypes] = React.useState(SUPPORTED_EXTENSIONS);

  return (
    <div className="flex flex-col gap-4 items-center justify-center py-12">
      <h1 className="text-2xl font-bold">Upload</h1>
      <p className="text-gray-500 text-sm">
        Upload your files to scan for PII data.
        <br />
        <span className="font-medium"> Supported file types:</span>
        {supportedFileTypes.join(",")}
      </p>

      <PiiSentinelUI allowedTypes={SUPPORTED_EXTENSIONS} />
    </div>
  );
}

export default Upload;
