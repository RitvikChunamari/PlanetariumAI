import React, { useEffect } from 'react';

export interface ImageData {
  local_path: string;
  title: string;
  description: string;
  date: string;
  source: string;
}

interface AstroMediaViewerProps {
  image: ImageData | null;
  onClose?: () => void;
}

export const AstroMediaViewer: React.FC<AstroMediaViewerProps> = ({ image, onClose }) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && onClose) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!image) return null;

  const imageSrc = image.local_path.startsWith('http')
    ? image.local_path
    : `${image.local_path.startsWith('/') ? '' : '/'}${image.local_path}`;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-8 bg-black/85 backdrop-blur-xl animate-in fade-in duration-200"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={image.title}
    >
      <div 
        className="relative w-full max-w-5xl max-h-[92vh] overflow-y-auto rounded-2xl bg-[#0c0d12] border border-white/10 shadow-2xl p-6 sm:p-8 flex flex-col lg:flex-row gap-8 items-start"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        {onClose && (
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 rounded-full bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition-colors z-10"
            aria-label="Close image viewer"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}

        {/* Primary Specimen Frame */}
        <div className="w-full lg:w-7/12 flex-shrink-0 rounded-xl overflow-hidden bg-black/80 border border-white/5 flex items-center justify-center">
          <img
            src={imageSrc}
            alt={image.title}
            className="w-full h-auto max-h-[68vh] object-contain"
          />
        </div>

        {/* Museum Curatorial Plaque */}
        <div className="w-full lg:w-5/12 flex flex-col justify-between self-stretch">
          <div className="space-y-4">
            <div className="inline-flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
              <span className="text-[11px] font-mono tracking-wider text-zinc-400 uppercase">
                NASA Observation Archive
              </span>
            </div>

            <h2 className="text-xl sm:text-2xl font-semibold tracking-tight text-white leading-tight">
              {image.title}
            </h2>

            <dl className="grid grid-cols-2 gap-3 py-3 border-y border-white/10 text-xs font-mono">
              <div>
                <dt className="text-zinc-500 text-[10px] uppercase">Archive Source</dt>
                <dd className="text-zinc-300 font-medium mt-0.5 truncate">{image.source || 'NASA / JPL'}</dd>
              </div>
              <div>
                <dt className="text-zinc-500 text-[10px] uppercase">Acquisition Date</dt>
                <dd className="text-zinc-300 font-medium mt-0.5">
                  {image.date ? image.date.substring(0, 10) : 'Archived Record'}
                </dd>
              </div>
            </dl>

            <div className="max-h-[36vh] overflow-y-auto pr-2">
              <p className="text-sm text-zinc-300 leading-relaxed font-normal">
                {image.description}
              </p>
            </div>
          </div>

          <div className="pt-4 border-t border-white/5 flex items-center justify-between text-xs font-mono text-zinc-500">
            <span>PALOMAR EXHIBIT GALLERY</span>
            <span>ESC TO DISMISS</span>
          </div>
        </div>
      </div>
    </div>
  );
};
