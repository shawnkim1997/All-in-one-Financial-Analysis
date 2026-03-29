"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[ATLAS] route error:", error);
  }, [error]);

  return (
    <div className="min-h-[50vh] flex flex-col items-center justify-center p-8 bg-bg-primary text-text-primary">
      <p className="text-accent-red font-mono text-sm mb-2">An error occurred while rendering this page.</p>
      <p className="text-text-muted text-xs font-mono text-center max-w-md mb-6 break-words">
        {error.message || "Unknown error"}
      </p>
      <button
        type="button"
        onClick={() => reset()}
        className="px-4 py-2 rounded-lg bg-accent-green text-bg-primary font-mono text-sm hover:opacity-90"
      >
        Retry
      </button>
      <p className="text-text-muted text-xs mt-8 text-center max-w-lg">
        If you see a blank screen, check the browser developer tools (F12) → Console tab for red error messages, or run{" "}
        <code className="text-accent-blue">rm -rf .next && npm run dev</code> in your terminal to clear the cache and restart.
      </p>
    </div>
  );
}
