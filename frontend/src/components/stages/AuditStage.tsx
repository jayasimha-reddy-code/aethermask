import { FileDown, ScanLine } from 'lucide-react';
import type { ObfuscateResponse } from '../../lib/types';
import { manifestToFile, type VerifyResponse } from '../../lib/api';
import { Button, Panel, PanelHeader } from '../ui/Primitives';
import { AuditPanel } from '../audit/AuditPanel';

export interface AuditFiles {
  original: File | null;
  setOriginal: (f: File | null) => void;
  sanitized: File | null;
  setSanitized: (f: File | null) => void;
  map: File | null;
  setMap: (f: File | null) => void;
  passphrase: string;
  setPassphrase: (p: string) => void;
}

export interface AuditSessionSource {
  result: ObfuscateResponse | null;
  file: File | null;
  passphrase: string;
}

export interface AuditStageProps {
  files: AuditFiles;
  session: AuditSessionSource;
  auditResult: VerifyResponse | null;
  busy: string | null;
  runAudit: () => Promise<void>;
  showNotice: (title: string, desc: string) => void;
}

export function AuditStage({
  files,
  session,
  auditResult,
  busy,
  runAudit,
  showNotice,
}: AuditStageProps) {
  const {
    original: auditOriginal,
    setOriginal: setAuditOriginal,
    sanitized: auditSanitized,
    setSanitized: setAuditSanitized,
    map: auditMap,
    setMap: setAuditMap,
    passphrase: auditPassphrase,
    setPassphrase: setAuditPassphrase,
  } = files;

  const { result, file, passphrase } = session;

  return (
    <Panel>
      <PanelHeader
        icon={<ScanLine size={15} />}
        title="6 · Independent isomorphism audit"
        subtitle="Recomputes aggregates directly from raw files without engine bias"
        actions={
          result && file ? (
            <Button
              tone="ghost"
              icon={<FileDown size={13} />}
              onClick={() => {
                setAuditOriginal(file);
                setAuditSanitized(
                  new File(
                    [
                      Uint8Array.from(atob(result.artifact.base64), (c) =>
                        c.charCodeAt(0),
                      ),
                    ],
                    result.artifact.filename,
                    { type: result.artifact.mime_type },
                  ),
                );
                setAuditMap(
                  manifestToFile(
                    result.ciphermap.manifest,
                    result.ciphermap.filename,
                  ),
                );
                setAuditPassphrase(passphrase);
                showNotice(
                  'Session inputs loaded',
                  'Original, artifact and vault loaded from current workspace',
                );
              }}
            >
              Load current session
            </Button>
          ) : undefined
        }
      />
      <div className="p-5">
        <AuditPanel
          originalFile={auditOriginal}
          sanitizedFile={auditSanitized}
          ciphermapFile={auditMap}
          onOriginal={setAuditOriginal}
          onSanitized={setAuditSanitized}
          onCiphermap={setAuditMap}
          passphrase={auditPassphrase}
          onPassphrase={setAuditPassphrase}
          result={auditResult}
          busy={busy !== null}
          onRun={() => void runAudit()}
        />
      </div>
    </Panel>
  );
}
