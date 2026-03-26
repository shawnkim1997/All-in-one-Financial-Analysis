"use client";

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
} from "react";

export type FilingSectionTab = {
  key: string;
  label: string;
  short: string;
  anchorId: string;
};

export type FilingsViewerHandle = {
  scrollToAnchor: (anchorId: string) => void;
};

type Props = {
  html: string;
  sections: FilingSectionTab[];
  activeSection: string;
  onActiveSectionChange: (key: string) => void;
};

export const FilingsViewer = forwardRef<FilingsViewerHandle, Props>(function FilingsViewer(
  { html, sections, activeSection, onActiveSectionChange },
  ref,
) {
  const scrollRootRef = useRef<HTMLDivElement | null>(null);
  const activeSectionRef = useRef(activeSection);
  activeSectionRef.current = activeSection;

  const scrollToAnchor = useCallback((anchorId: string) => {
    const root = scrollRootRef.current;
    if (!root) return;
    const el = root.querySelector(`#${CSS.escape(anchorId)}`);
    if (el && "scrollIntoView" in el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      scrollToAnchor,
    }),
    [scrollToAnchor],
  );

  useEffect(() => {
    const root = scrollRootRef.current;
    if (!root || !html) return;

    const ids = sections.map((s) => s.anchorId).filter(Boolean);
    const elements = ids
      .map((id) => root.querySelector(`#${CSS.escape(id)}`))
      .filter((n): n is Element => n !== null);
    if (elements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting && e.target.id)
          .sort((a, b) => {
            const ra = a.boundingClientRect.top;
            const rb = b.boundingClientRect.top;
            return ra - rb;
          });
        if (visible.length === 0) return;
        const top = visible[0]?.target.id;
        if (!top) return;
        const sec = sections.find((s) => s.anchorId === top);
        if (sec && sec.key !== activeSectionRef.current) {
          onActiveSectionChange(sec.key);
        }
      },
      {
        root,
        rootMargin: "-12% 0px -55% 0px",
        threshold: [0, 0.05, 0.1, 0.25, 0.5],
      },
    );

    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [html, sections, onActiveSectionChange]);

  return (
    <div className="border border-border rounded-lg bg-bg-card overflow-hidden flex flex-col max-h-[min(72vh,calc(100vh-200px))]">
      <div
        ref={scrollRootRef}
        className="overflow-y-auto flex-1 min-h-0 scroll-smooth"
        style={{ WebkitOverflowScrolling: "touch" }}
      >
        <div className="overflow-x-auto min-w-0">
          <div
            className="sec-viewer-container max-w-none p-4 md:p-6 pb-10"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        </div>
      </div>
    </div>
  );
});
