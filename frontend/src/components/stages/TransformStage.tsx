import { ArrowLeft, ArrowLeftRight, Lock } from 'lucide-react';
import { AnimatePresence, m } from 'motion/react';
import { easeQuick } from '../../lib/motion';
import { formatBytes } from '../../lib/format';
import type {
  DomainProfileInfo,
  NumericMode,
  ProfileResponse,
  Stage,
} from '../../lib/types';
import type { PreviewResponse } from '../../lib/api';
import { Button, Field, Panel, PanelHeader, inputClass } from '../ui/Primitives';
import { NumericModeToggle, PassphraseField, ProfilePicker } from '../pipeline/Controls';
import { DryRunPreview } from '../pipeline/DryRunPreview';

export interface TransformConfig {
  profiles: DomainProfileInfo[];
  selectedProfile: string;
  setSelectedProfile: (p: string) => void;
  profile: ProfileResponse | null;
  numericMode: NumericMode;
  setNumericMode: (m: NumericMode) => void;
  passphrase: string;
  setPassphrase: (p: string) => void;
  seed: string;
  setSeed: (s: string) => void;
}

export interface TransformDryRun {
  showDryRun: boolean;
  setShowDryRun: (fn: (v: boolean) => boolean) => void;
  dryRun: PreviewResponse | null;
  runDryRun: () => Promise<void>;
}

export interface TransformStageProps {
  config: TransformConfig;
  dryRun: TransformDryRun;
  file: File | null;
  busy: string | null;
  runObfuscate: () => Promise<void>;
  go: (s: Stage) => void;
}

export function TransformStage({
  config,
  dryRun,
  file,
  busy,
  runObfuscate,
  go,
}: TransformStageProps) {
  const {
    profiles,
    selectedProfile,
    setSelectedProfile,
    profile,
    numericMode,
    setNumericMode,
    passphrase,
    setPassphrase,
    seed,
    setSeed,
  } = config;

  const {
    showDryRun,
    setShowDryRun,
    dryRun: dryRunData,
    runDryRun,
  } = dryRun;

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
      <Panel>
        <PanelHeader
          icon={<ArrowLeftRight size={15} />}
          title="3 · Isomorphic transformation"
          subtitle="Select the target non-classified cover domain"
        />
        <div className="space-y-6 p-5">
          <div>
            <h3 className="mb-2 text-xs font-medium text-slate-300">
              Cover domain profile
            </h3>
            {profiles.length > 0 ? (
              <ProfilePicker
                profiles={profiles}
                selected={selectedProfile}
                onSelect={setSelectedProfile}
                recommended={profile?.recommended_profile}
              />
            ) : (
              <div className="rounded-lg border border-white/8 bg-abyss-850/50 p-6 text-center text-xs text-slate-500">
                Loading local profile catalogue…
              </div>
            )}
          </div>

          <div>
            <h3 className="mb-2 text-xs font-medium text-slate-300">
              Numbers &amp; coordinates
            </h3>
            <NumericModeToggle mode={numericMode} onChange={setNumericMode} />
          </div>

          <div className="hairline" />

          <div>
            <div className="mb-2 flex items-center justify-between gap-3">
              <h3 className="text-xs font-medium text-slate-300">
                Dry-run rehearsal
              </h3>
              <button
                type="button"
                onClick={() => setShowDryRun((v) => !v)}
                aria-expanded={showDryRun}
                className="text-xs text-slate-400 outline-none hover:text-slate-200 transition-colors"
              >
                {showDryRun ? 'Hide' : 'Show preview'}
              </button>
            </div>
            <AnimatePresence initial={false}>
              {showDryRun ? (
                <m.div
                  key="dryrun"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={easeQuick}
                  className="overflow-hidden"
                >
                  <DryRunPreview
                    preview={dryRunData}
                    busy={busy !== null}
                    canRun={!!file && busy === null}
                    onRun={() => void runDryRun()}
                    profileTitle={
                      profiles.find((p) => p.key === selectedProfile)?.title ?? ''
                    }
                  />
                </m.div>
              ) : null}
            </AnimatePresence>
          </div>
        </div>
      </Panel>

      <Panel>
        <PanelHeader
          icon={<Lock size={15} />}
          title="Vault configuration"
          subtitle="Passphrase remains exclusively in volatile memory"
        />
        <div className="space-y-4 p-5">
          <div className="rounded-lg border border-white/8 bg-abyss-850/60 p-3">
            <div className="text-xs text-slate-500">
              Source dataset
            </div>
            <div className="tabular mt-0.5 truncate text-xs font-medium text-slate-200">
              {file ? file.name : '(none selected)'}
            </div>
            {file ? (
              <div className="mt-0.5 text-xs text-slate-500">
                {formatBytes(file.size)}
              </div>
            ) : null}
          </div>

          <PassphraseField value={passphrase} onChange={setPassphrase} />

          <Field
            label="Determinism seed (optional)"
            htmlFor="seed"
            hint="Identical seed and profile yield bit-exact reproducible output"
          >
            <input
              id="seed"
              type="text"
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              placeholder="e.g. exercise-alpha-2026"
              spellCheck={false}
              className={inputClass}
            />
          </Field>

          <div className="hairline" />

          <div className="flex flex-col gap-2 pt-1">
            <Button
              tone="primary"
              icon={<Lock size={14} />}
              disabled={!file || passphrase.length < 8}
              busy={busy !== null}
              onClick={() => void runObfuscate()}
              className="w-full"
            >
              Mask &amp; seal vault
            </Button>
            <Button
              tone="ghost"
              icon={<ArrowLeft size={13} />}
              onClick={() => go(profile ? 'profile' : 'ingest')}
            >
              Back
            </Button>
          </div>
        </div>
      </Panel>
    </div>
  );
}
