import { ArrowLeft, ArrowRight, FileSearch, ScanSearch } from 'lucide-react';
import type { ProfileResponse, Stage } from '../../lib/types';
import { Button, EmptyState, Panel, PanelHeader } from '../ui/Primitives';
import { ProfilePanel } from '../pipeline/ProfilePanel';

export interface ProfileStageProps {
  profile: ProfileResponse | null;
  go: (s: Stage) => void;
}

export function ProfileStage({ profile, go }: ProfileStageProps) {
  return (
    <Panel>
      <PanelHeader
        icon={<ScanSearch size={15} />}
        title="2 · Sensitivity profile"
        subtitle="Rule-based offline inspection with evidence fragments redacted"
        actions={
          <div className="flex gap-2">
            <Button
              tone="ghost"
              icon={<ArrowLeft size={13} />}
              onClick={() => go('ingest')}
            >
              Back
            </Button>
            <Button
              tone="primary"
              icon={<ArrowRight size={13} />}
              onClick={() => go('transform')}
            >
              Configure transform
            </Button>
          </div>
        }
      />
      <div className="p-5">
        {profile ? (
          <ProfilePanel profile={profile} />
        ) : (
          <EmptyState icon={<FileSearch size={20} />} title="No profile generated">
            Return to ingest and run "Analyse sensitivity".
          </EmptyState>
        )}
      </div>
    </Panel>
  );
}
