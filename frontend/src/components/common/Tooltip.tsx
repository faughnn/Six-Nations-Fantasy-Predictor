import { useState, useRef, useEffect, type ReactNode } from 'react';

interface TooltipProps {
  text: string;
  children: ReactNode;
}

export function Tooltip({ text, children }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState<'top' | 'bottom'>('top');
  const triggerRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (visible && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPosition(rect.top < 60 ? 'bottom' : 'top');
    }
  }, [visible]);

  return (
    <span
      ref={triggerRef}
      className="relative inline-flex items-center"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {visible && (
        <span
          className={`absolute z-50 px-2.5 py-1.5 text-xs font-normal normal-case tracking-normal text-white bg-slate-800 rounded-lg shadow-lg whitespace-nowrap pointer-events-none ${
            position === 'top' ? 'bottom-full mb-1.5' : 'top-full mt-1.5'
          } left-1/2 -translate-x-1/2`}
        >
          {text}
          <span
            className={`absolute left-1/2 -translate-x-1/2 w-0 h-0 border-4 border-transparent ${
              position === 'top'
                ? 'top-full border-t-slate-800'
                : 'bottom-full border-b-slate-800'
            }`}
          />
        </span>
      )}
    </span>
  );
}
