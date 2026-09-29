import { type ReactNode, useEffect, useId } from 'react';
import { AnimatePresence, m } from 'motion/react';
import { X } from 'lucide-react';
import { backdropVariants, panelVariants } from '../../lib/motion';

export function Modal({
  open,
  onClose,
  title,
  children,
  width = 'max-w-2xl',
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  width?: string;
}) {
  const titleId = useId();

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open ? (
        <m.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          variants={backdropVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
        >
          <div
            className="absolute inset-0 bg-abyss-950/80 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden="true"
          />
          <m.div
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            className={`panel relative z-10 max-h-[85vh] w-full ${width} overflow-hidden`}
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <div className="flex items-center justify-between border-b border-white/8 px-5 py-4">
              <h2 id={titleId} className="text-sm font-medium text-slate-100">
                {title}
              </h2>
              <button
                type="button"
                onClick={onClose}
                className="rounded p-1 text-slate-400 outline-none hover:bg-abyss-800 hover:text-slate-100"
                aria-label="Close dialog"
              >
                <X size={16} />
              </button>
            </div>
            <div className="max-h-[calc(85vh-3.5rem)] overflow-auto p-5">
              {children}
            </div>
          </m.div>
        </m.div>
      ) : null}
    </AnimatePresence>
  );
}
