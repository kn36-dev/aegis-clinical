interface ClinicalContextCardProps {
  reasoningSummary?: string;
  normalizedNoteText?: string;
}

/** Renders the reasoning/context fields the API exposes for a pending review; renders nothing if absent. */
export function ClinicalContextCard({
  reasoningSummary,
  normalizedNoteText,
}: ClinicalContextCardProps) {
  if (!reasoningSummary && !normalizedNoteText) {
    return null;
  }

  return (
    <section className="clinical-context-card">
      <h2>Clinical Context</h2>
      {reasoningSummary && (
        <div className="clinical-context-card__block">
          <h3>AI Reasoning Summary</h3>
          <p>{reasoningSummary}</p>
        </div>
      )}
      {normalizedNoteText && (
        <div className="clinical-context-card__block">
          <h3>Normalized Note</h3>
          <p className="clinical-context-card__note">{normalizedNoteText}</p>
        </div>
      )}
    </section>
  );
}
