import type { WorkflowStageArtifact } from "../../../domain/workflow";

interface ArtifactJsonViewerProps {
  artifact: WorkflowStageArtifact;
}

/**
 * Renders one stage's raw backend artifact exactly as provided -- no
 * parsing, field-picking, or reshaping of ``payload``. See
 * aegis.api.schemas.workflow.WorkflowStageArtifact for what populates it
 * and the PHI/debug boundary that gates whether it is ever present.
 */
export function ArtifactJsonViewer({ artifact }: ArtifactJsonViewerProps) {
  return (
    <div
      className="artifact-json-viewer"
      role="region"
      aria-label={`${artifact.artifact_type} artifact`}
    >
      <p className="artifact-json-viewer__type">{artifact.artifact_type}</p>
      <pre className="artifact-json-viewer__payload">
        {JSON.stringify(artifact.payload, null, 2)}
      </pre>
    </div>
  );
}
