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
      <p className="text-accent-red font-mono text-sm mb-2">화면을 그리는 중 오류가 났습니다.</p>
      <p className="text-text-muted text-xs font-mono text-center max-w-md mb-6 break-words">
        {error.message || "Unknown error"}
      </p>
      <button
        type="button"
        onClick={() => reset()}
        className="px-4 py-2 rounded-lg bg-accent-green text-bg-primary font-mono text-sm hover:opacity-90"
      >
        다시 시도
      </button>
      <p className="text-text-muted text-xs mt-8 text-center max-w-lg">
        흰 화면만 보일 때는 브라우저 개발자 도구(F12) → Console 탭의 빨간 에러 메시지를 확인하거나, 터미널에서{" "}
        <code className="text-accent-blue">rm -rf .next && npm run dev</code> 로 캐시를 지우고 다시 실행해 보세요.
      </p>
    </div>
  );
}
