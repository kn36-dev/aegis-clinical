import React, { useState } from 'react';
import Dashboard from './views/Dashboard';
import ReviewConsole from './views/ReviewConsole';

export type ViewMode = 'physician' | 'researcher';

export interface PatientCase {
  case_id: string;
  patient_id: string;
  status: 'PENDING_AI' | 'PENDING_HITL' | 'ARCHIVED';
  ingress_timestamp: string;
  raw_clinical_note: string;
  extracted_codes?: Array<{ code: string; title: string; confidence_score: number }>;
}

export default function App() {
  const [viewMode, setViewMode] = useState<ViewMode>('physician');

  // Shared mock state simulating a real database connection for verification loops
  const [cases, setCases] = useState<PatientCase[]>([
    {
      case_id: "c8f14b62-7e21-41fa-9b93-b6d859a72df1",
      patient_id: "p-99102-x",
      status: "PENDING_HITL",
      ingress_timestamp: "2026-06-16 09:40:00",
      raw_clinical_note: "Patient [PATIENT_NAME_1] presented with acute onset of severe watery diarrhea, frequently described as 'rice-water' stools. Complaining of severe muscle cramps and dehydration.",
      extracted_codes: [{ code: "1A00", title: "Cholera", confidence_score: 0.942 }]
    },
    {
      case_id: "a3b9cc24-019d-4e2a-8bf8-d44a2b109e99",
      patient_id: "p-41223-y",
      status: "PENDING_AI",
      ingress_timestamp: "2026-06-16 08:12:00",
      raw_clinical_note: "Infant presentation. 14-month-old male presenting with low-grade fever, acute non-stop vomiting for 48 hours, followed by watery diarrhea."
    }
  ]);

  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(cases[0]?.case_id || null);
  const activeCase = cases.find(c => c.case_id === selectedCaseId) || null;

  // Handles trial submissions by adding a simulated raw patient log to illustrate pipeline processing
  const handleTrialIngestion = (trialPayload: any) => {
    alert(`🔬 Pipeline Action Triggered!\nSent trial ${trialPayload.trial_id} to PydanticAI model extraction.\nRaw Text Length: ${trialPayload.raw_eligibility_criteria.length} characters.`);
  };

  return (
    <div style={{ fontFamily: 'monospace', padding: '20px', backgroundColor: '#f9f9f9', minHeight: '100vh', color: '#333' }}>
      <header style={{ borderBottom: '2px solid #333', paddingBottom: '10px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, color: 'black' }}>🛡️ AEGIS CLINICAL ENGINE</h2>
        <div>
          <button
            onClick={() => setViewMode('physician')}
            style={{ padding: '8px 16px', marginRight: '10px', cursor: 'pointer', backgroundColor: viewMode === 'physician' ? '#333' : '#eee', color: viewMode === 'physician' ? '#fff' : '#333', border: '1px solid #333' }}
          >
            Physician Workspace
          </button>
          <button
            onClick={() => setViewMode('researcher')}
            style={{ padding: '8px 16px', cursor: 'pointer', backgroundColor: viewMode === 'researcher' ? '#333' : '#eee', color: viewMode === 'researcher' ? '#fff' : '#333', border: '1px solid #333' }}
          >
            Researcher Console
          </button>
        </div>
      </header>

      {viewMode === 'physician' ? (
        <div style={{ display: 'flex', gap: '20px' }}>
          <div style={{ maxWidth: '75%', flex: 1, border: '1px solid #ccc', padding: '15px', backgroundColor: '#fff' }}>
            <Dashboard cases={cases} onSelectCase={setSelectedCaseId} selectedCaseId={selectedCaseId} />
          </div>
          <div style={{ flex: 1, border: '1px solid #ccc', padding: '15px', backgroundColor: '#fff' }}>
            <ReviewConsole activeCase={activeCase} setCases={setCases} />
          </div>
        </div>
      ) : (
        <div style={{ border: '1px solid #ccc', padding: '20px', backgroundColor: '#fff' }}>
          <h3>🧬 Clinical Trial Registry Ingestion Workspace</h3>
          <p style={{ color: '#666', fontSize: '12px' }}>Simulates pulling unstructured protocols directly from external public feeds like ClinicalTrials.gov.</p>
          <ResearcherForm onSubmit={handleTrialIngestion} />
        </div>
      )}
    </div>
  );
}

interface ResearcherFormProps {
  onSubmit: (payload: any) => void;
}

function ResearcherForm({ onSubmit }: ResearcherFormProps) {
  const [formData, setFormData] = useState({
    trial_id: 'NCT05912345',
    title: 'Phase II Efficacy and Safety Study Evaluating Therapeutic Targets for Watery Diarrhea Outbreaks',
    sponsor: 'BioPharma Global Research',
    phase: 'Phase 2',
    status: 'RECRUITING',
    raw_eligibility_criteria: 'Inclusion Criteria:\n- Adults aged 18 to 65 years baseline.\n- Clinical presentation matches acute severe watery diarrhea consistent with Cholera vector maps.\n\nExclusion Criteria:\n- History of prior vaccine deployment within 30 days.\n- Severe cardiovascular co-morbidities.'
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginTop: '15px' }}>
      <div style={{ display: 'flex', gap: '15px' }}>
        <label style={{ flex: 1 }}>Trial ID:
          <input type="text" value={formData.trial_id} onChange={e => setFormData({ ...formData, trial_id: e.target.value })} style={{ width: '100%', padding: '6px', marginTop: '5px', border: '1px solid #aaa' }} />
        </label>
        <label style={{ flex: 2 }}>Full Title:
          <input type="text" value={formData.title} onChange={e => setFormData({ ...formData, title: e.target.value })} style={{ width: '100%', padding: '6px', marginTop: '5px', border: '1px solid #aaa' }} />
        </label>
      </div>
      <div style={{ display: 'flex', gap: '15px' }}>
        <label style={{ flex: 1 }}>Sponsor Institution:
          <input type="text" value={formData.sponsor} onChange={e => setFormData({ ...formData, sponsor: e.target.value })} style={{ width: '100%', padding: '6px', marginTop: '5px', border: '1px solid #aaa' }} />
        </label>
        <label style={{ flex: 1 }}>Phase Tier:
          <select value={formData.phase} onChange={e => setFormData({ ...formData, phase: e.target.value })} style={{ width: '100%', padding: '6px', marginTop: '5px', border: '1px solid #aaa' }}>
            <option value="Phase 1">Phase 1</option>
            <option value="Phase 2">Phase 2</option>
            <option value="Phase 3">Phase 3</option>
          </select>
        </label>
      </div>
      <label>Raw Eligibility Criteria Text Box (Unstructured Ingress Input):
        <textarea rows={8} value={formData.raw_eligibility_criteria} onChange={e => setFormData({ ...formData, raw_eligibility_criteria: e.target.value })} style={{ width: '100%', padding: '8px', marginTop: '5px', boxSizing: 'border-box', border: '1px solid #aaa', fontFamily: 'monospace' }} />
      </label>
      <button type="submit" style={{ padding: '10px', backgroundColor: '#0066cc', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 'bold' }}>
        📥 Run AI Ingestion and Hydrate Target Junction Table
      </button>
    </form>
  );
}