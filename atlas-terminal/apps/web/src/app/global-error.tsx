"use client";

/**
 * Root error UI when the root layout fails. Must define html/body (Next.js requirement).
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, background: "#0a0a0f", color: "#e5e7eb", fontFamily: "system-ui, sans-serif", padding: 24 }}>
        <h2 style={{ color: "#ff4757" }}>ATLAS Terminal — fatal error</h2>
        <p style={{ fontSize: 14, marginTop: 8 }}>{error.message || "Unknown error"}</p>
        <button
          type="button"
          onClick={() => reset()}
          style={{
            marginTop: 16,
            padding: "8px 16px",
            background: "#00d4aa",
            color: "#0a0a0f",
            border: "none",
            borderRadius: 6,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Try again
        </button>
      </body>
    </html>
  );
}
