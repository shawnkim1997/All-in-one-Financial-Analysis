import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-bold text-text-primary">404</h1>
      <p className="text-text-muted">This page does not exist.</p>
      <Link
        href="/"
        className="rounded-md bg-accent-green px-4 py-2 text-sm font-semibold text-bg-primary no-underline hover:opacity-90"
      >
        Back to Overview
      </Link>
    </div>
  );
}
