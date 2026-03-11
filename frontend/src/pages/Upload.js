import React from "react";
import PiiSentinelUI from "../components/PiiSentinelUI";

import { FALLBACK_SUPPORTED_EXTENSIONS, fetchSupportedFileTypes } from "../utils/fileTypes";

function Upload() {
  const [supportedFileTypes, setSupportedFileTypes] = React.useState(FALLBACK_SUPPORTED_EXTENSIONS);

  React.useEffect(() => {
    let active = true;

    fetchSupportedFileTypes()
      .then((extensions) => {
        if (active) {
          setSupportedFileTypes(extensions);
        }
      })
      .catch(() => {
        if (active) {
          setSupportedFileTypes(FALLBACK_SUPPORTED_EXTENSIONS);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="page-shell flex flex-col items-center justify-center gap-4 py-12">
      <h1 className="text-2xl font-bold text-app">Upload</h1>
      <p className="text-app-secondary text-sm">
        Upload your files to scan for PII data.
        <br />
        <span className="font-medium"> Supported file types:</span>
        {supportedFileTypes.join(",")}
      </p>

      <PiiSentinelUI allowedTypes={supportedFileTypes} />
    </div>
  );
}

export default Upload;
