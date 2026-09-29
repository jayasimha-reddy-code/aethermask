import {
  Activity,
  ArrowRight,
  Database,
  FileStack,
  Fingerprint,
  Lock,
  ScanSearch,
  ShieldCheck,
} from 'lucide-react';
import type { AttestationResponse, ObfuscateResponse, ProfileResponse, Stage } from '../../lib/types';
import { formatInt } from '../../lib/format';
import { Button, Field, Panel, PanelHeader, Stat, inputClass } from '../ui/Primitives';
import { DropZone } from '../pipeline/Controls';

export interface IngestStageProps {
  file: File | null;
  setFile: (f: File | null) => void;
  setProfile: (p: ProfileResponse | null) => void;
  setResult: (r: ObfuscateResponse | null) => void;
  datasetName: string;
  setDatasetName: (name: string) => void;
  busy: string | null;
  runProfile: () => Promise<void>;
  go: (s: Stage) => void;
  attestation: AttestationResponse | null;
  acceptData: string;
}

export function IngestStage({
  file,
  setFile,
  setProfile,
  setResult,
  datasetName,
  setDatasetName,
  busy,
  runProfile,
  go,
  attestation,
  acceptData,
}: IngestStageProps) {
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
      <Panel>
        <PanelHeader
          icon={<Database size={15} />}
          title="1 · Ingest source dataset"
          subtitle="Parsed in local memory and never persisted or transmitted"
        />
        <div className="space-y-4 p-5">
          <DropZone
            file={file}
            onFile={(f) => {
              setFile(f);
              setProfile(null);
              setResult(null);
              if (f && !datasetName) {
                setDatasetName(f.name.replace(/\.[^.]+$/, ''));
              }
            }}
            accept={acceptData}
            label="Drop a dataset here, or click to browse"
            hint="CSV · TSV · Parquet · XLSX · XLS · JSON · .sql dump"
          />

          <Field
            label="Dataset name"
            htmlFor="dataset-name"
            hint="Labels tables and the emitted artifact"
          >
            <input
              id="dataset-name"
              type="text"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              placeholder="e.g. classified_missions"
              className={inputClass}
            />
          </Field>

          <div className="flex flex-wrap gap-2 pt-1">
            <Button
              tone="primary"
              icon={<ScanSearch size={14} />}
              disabled={!file}
              busy={busy !== null}
              onClick={() => void runProfile()}
            >
              Analyse sensitivity
            </Button>
            <Button
              tone="neutral"
              icon={<ArrowRight size={14} />}
              disabled={!file}
              onClick={() => go('transform')}
            >
              Skip to transform
            </Button>
          </div>
        </div>
      </Panel>

      <div className="space-y-5">
        <Panel>
          <PanelHeader
            icon={<ShieldCheck size={15} />}
            title="Offline verification guarantees"
            subtitle="Enforced by architecture and air-gap sentinel"
          />
          <ul className="space-y-2.5 p-5">
            {[
              {
                Icon: ShieldCheck,
                title: 'Zero external network calls',
                body: 'No LLM APIs, external fonts, telemetry or CDNs. Browser egress watchdog halts any outbound attempt.',
              },
              {
                Icon: Activity,
                title: 'Mathematical isomorphism',
                body: 'Categorical multisets, cardinality, null topologies and query aggregates are provably preserved.',
              },
              {
                Icon: Fingerprint,
                title: 'Deterministic bijectivity',
                body: 'Every entity maps one-to-one without many-to-one collisions, guaranteeing lossless inversion.',
              },
              {
                Icon: Lock,
                title: 'Cryptographic vault',
                body: 'Argon2id key derivation, HMAC-SHA256 integrity, AES-256-GCM cipher with schema binding.',
              },
            ].map(({ Icon, title, body }) => (
              <li
                key={title}
                className="flex gap-3 rounded-lg border border-white/8 bg-abyss-850/50 p-3"
              >
                <Icon
                  size={14}
                  className="mt-0.5 shrink-0 text-slate-400"
                  aria-hidden="true"
                />
                <div>
                  <div className="text-xs font-medium text-slate-200">
                    {title}
                  </div>
                  <p className="mt-0.5 text-xs leading-relaxed text-slate-400">
                    {body}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </Panel>

        {attestation?.lexicon ? (
          <Panel>
            <PanelHeader
              icon={<FileStack size={15} />}
              title="Local lexicon capacity"
              subtitle="Deterministic surrogate pools vendored within the air-gap"
            />
            <div className="grid grid-cols-2 gap-3 p-5">
              <Stat
                label="Cover domains"
                value={formatInt(attestation.lexicon.profiles)}
              />
              <Stat
                label="Surrogate entities"
                value={formatInt(attestation.lexicon.total_unique_surrogates)}
              />
              <Stat
                label="Token shift rules"
                value={formatInt(attestation.lexicon.total_token_shift_rules)}
              />
              <Stat
                label="Pattern detectors"
                value={`${formatInt(attestation.lexicon.sensitivity_rules)} + ${formatInt(attestation.lexicon.ner_patterns)}`}
                hint="Sensitivity + offline NER"
              />
            </div>
          </Panel>
        ) : null}
      </div>
    </div>
  );
}
