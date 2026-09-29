export function StudioFooter() {
  return (
    <footer className="mx-auto max-w-[1600px] px-6 pt-2 pb-8">
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/8 pt-4 text-xs text-slate-500">
        <span>
          AetherMask · CipherShift: local processing only. Zero external egress.
        </span>
        <div className="flex flex-wrap items-center gap-4">
          <span className="tabular">AES-256-GCM · Argon2id</span>
          <span>Offline verification sentinel</span>
        </div>
      </div>
    </footer>
  );
}
