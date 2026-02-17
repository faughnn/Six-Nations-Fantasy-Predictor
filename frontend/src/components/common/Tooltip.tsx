import { useState, useRef, useEffect, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

interface TooltipProps {
  text: string;
  children: ReactNode;
}

export function Tooltip({ text, children }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0, below: false });
  const triggerRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (visible && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      const below = rect.top < 40;
      setCoords({
        top: below ? rect.bottom + 6 : rect.top - 6,
        left: rect.left + rect.width / 2,
        below,
      });
    }
  }, [visible]);

  return (
    <span
      ref={triggerRef}
      className="inline-flex items-center"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {visible && createPortal(
        <span
          className="fixed z-[9999] px-2.5 py-1.5 text-xs font-normal normal-case tracking-normal text-white bg-slate-800 rounded-lg shadow-lg whitespace-nowrap pointer-events-none -translate-x-1/2"
          style={{
            top: coords.below ? coords.top : undefined,
            bottom: coords.below ? undefined : `${window.innerHeight - coords.top}px`,
            left: coords.left,
          }}
        >
          {text}
          <span
            className={`absolute left-1/2 -translate-x-1/2 w-0 h-0 border-4 border-transparent ${
              coords.below
                ? 'bottom-full border-b-slate-800'
                : 'top-full border-t-slate-800'
            }`}
          />
        </span>,
        document.body
      )}
    </span>
  );
}
