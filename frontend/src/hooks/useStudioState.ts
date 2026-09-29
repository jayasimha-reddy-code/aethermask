import { useEffect, useMemo, useState } from 'react';
import type {
  AttestationResponse,
  DomainProfileInfo,
  NumericMode,
  ObfuscateResponse,
  ProfileResponse,
  RestoreResponse,
  Stage,
} from '../lib/types';
import type { PreviewResponse, VerifyResponse } from '../lib/api';
import { fetchAttestation, fetchProfiles } from '../lib/api';
import { useEgressWatch } from './useEgressWatch';
import { useToasts } from '../components/ui/Toasts';
import { usePipelineStageReducer } from './usePipelineStageReducer';

async function bootstrapCatalogue(
  signal: AbortSignal,
  onSuccess: (profiles: DomainProfileInfo[], attestation: AttestationResponse) => void,
  onError: (msg: string) => void,
) {
  try {
    const [cat, att] = await Promise.all([
      fetchProfiles(signal),
      fetchAttestation(signal),
    ]);
    onSuccess(cat.profiles, att);
  } catch (e) {
    if (!signal.aborted) {
      onError(
        e instanceof Error
          ? `Could not reach the local AetherMask service: ${e.message}`
          : 'Could not reach the local AetherMask service',
      );
    }
  }
}

function useBootstrap(
  selectedProfile: string,
  setSelectedProfile: (p: string) => void,
  setProfiles: (ps: DomainProfileInfo[]) => void,
  setAttestation: (a: AttestationResponse) => void,
  setError: (e: string | null) => void,
) {
  useEffect(() => {
    const ac = new AbortController();
    void bootstrapCatalogue(
      ac.signal,
      (catProfiles, att) => {
        setProfiles(catProfiles);
        setAttestation(att);
        const match = catProfiles.some((p) => p.key === selectedProfile);
        if (catProfiles.length > 0 && !match) {
          setSelectedProfile(catProfiles[0].key);
        }
      },
      setError,
    );
    return function cleanup() {
      ac.abort();
    };
  }, []);
}

function clearTimer(timerId: number) {
  window.clearTimeout(timerId);
}

function onTimeout(setNotice: (n: string | null) => void) {
  setNotice(null);
}

function useNoticeAutoClear(
  notice: string | null,
  setNotice: (n: string | null) => void,
) {
  useEffect(() => {
    if (!notice) return undefined;
    const t = window.setTimeout(onTimeout, 4200, setNotice);
    return () => clearTimer(t);
  }, [notice, setNotice]);
}

function computeReachable(file: File | null, result: ObfuscateResponse | null): Set<Stage> {
  const s = new Set<Stage>(['ingest']);
  if (file) {
    s.add('profile');
    s.add('transform');
  }
  if (result) {
    s.add('export');
  }
  s.add('restore');
  s.add('audit');
  return s;
}

export function useStudioState() {
  const { stage, direction, go: dispatchStage } = usePipelineStageReducer('ingest');
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [datasetName, setDatasetName] = useState('');
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [profiles, setProfiles] = useState<DomainProfileInfo[]>([]);
  const [attestation, setAttestation] = useState<AttestationResponse | null>(null);
  const [showAttestation, setShowAttestation] = useState(false);

  const [selectedProfile, setSelectedProfile] = useState('defense_to_logistics');
  const [numericMode, setNumericMode] = useState<NumericMode>('identity');
  const [passphrase, setPassphrase] = useState('');
  const [seed, setSeed] = useState('');
  const [result, setResult] = useState<ObfuscateResponse | null>(null);

  const [rFile, setRFile] = useState<File | null>(null);
  const [rMap, setRMap] = useState<File | null>(null);
  const [rPassphrase, setRPassphrase] = useState('');
  const [rResult, setRResult] = useState<RestoreResponse | null>(null);

  const [dryRun, setDryRun] = useState<PreviewResponse | null>(null);
  const [showDryRun, setShowDryRun] = useState(false);

  const [auditOriginal, setAuditOriginal] = useState<File | null>(null);
  const [auditSanitized, setAuditSanitized] = useState<File | null>(null);
  const [auditMap, setAuditMap] = useState<File | null>(null);
  const [auditPassphrase, setAuditPassphrase] = useState('');
  const [auditResult, setAuditResult] = useState<VerifyResponse | null>(null);

  const [paletteOpen, setPaletteOpen] = useState(false);

  const egress = useEgressWatch();
  const toasts = useToasts();

  useBootstrap(selectedProfile, setSelectedProfile, setProfiles, setAttestation, setError);
  useNoticeAutoClear(notice, setNotice);

  const go = dispatchStage;
  const reachable = useMemo(function calcReachable() {
    return computeReachable(file, result);
  }, [file, result]);

  return {
    stage,
    direction,
    go,
    reachable,
    busy,
    setBusy,
    error,
    setError,
    notice,
    setNotice,
    file,
    setFile,
    datasetName,
    setDatasetName,
    profile,
    setProfile,
    profiles,
    setProfiles,
    attestation,
    setAttestation,
    showAttestation,
    setShowAttestation,
    selectedProfile,
    setSelectedProfile,
    numericMode,
    setNumericMode,
    passphrase,
    setPassphrase,
    seed,
    setSeed,
    result,
    setResult,
    rFile,
    setRFile,
    rMap,
    setRMap,
    rPassphrase,
    setRPassphrase,
    rResult,
    setRResult,
    dryRun,
    setDryRun,
    showDryRun,
    setShowDryRun,
    auditOriginal,
    setAuditOriginal,
    auditSanitized,
    setAuditSanitized,
    auditMap,
    setAuditMap,
    auditPassphrase,
    setAuditPassphrase,
    auditResult,
    setAuditResult,
    paletteOpen,
    setPaletteOpen,
    egress,
    toasts,
  };
}

export type StudioState = ReturnType<typeof useStudioState>;
