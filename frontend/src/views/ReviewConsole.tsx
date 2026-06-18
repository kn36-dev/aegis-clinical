import React from 'react';
import type { PatientCase } from '../App';

interface ReviewConsoleProps {
    activeCase: PatientCase | null;
    setCases: React.Dispatch<React.SetStateAction<PatientCase[]>>;
}

export default function ReviewConsole({ activeCase, setCases }: ReviewConsoleProps) {
    if (!activeCase) {
        return <div style={{ color: '#666', textAlign: 'center', marginTop: '40px' }}>Select an active record row to load verification view.</div>;
    }

    const updateStatus = (newStatus: 'PENDING_AI' | 'PENDING_HITL' | 'ARCHIVED') => {
        setCases(prev => prev.map(c => c.case_id === activeCase.case_id ? { ...c, status: newStatus } : c));
        alert(`Success: Case status transitioned safely to [${newStatus}].`);
    };

    return (
        <div>
            <h3 style={{ margin: '0 0 15px 0', borderBottom: '1px dashed #333', paddingBottom: '5px' }}>
                🔍 HUMAN-IN-THE-LOOP AUDIT CONSOLE
            </h3>

            <div style={{ marginBottom: '15px', backgroundColor: '#fdfdfd', padding: '10px', border: '1px solid #eee' }}>
                <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
                    <tbody>
                        <tr>
                            <td style={{ fontWeight: 'bold', width: '120px', padding: '4px 0' }}>Case ID:</td>
                            <td>{activeCase.case_id}</td>
                        </tr>
                        <tr>
                            <td style={{ fontWeight: 'bold', padding: '4px 0' }}>Patient Anchor:</td>
                            <td>{activeCase.patient_id} <span style={{ color: '#00aa00', fontSize: '11px' }}>(🔒 PHI Token Sanitized)</span></td>
                        </tr>
                        <tr>
                            <td style={{ fontWeight: 'bold', padding: '4px 0' }}>Pipeline State:</td>
                            <td><span style={{ fontWeight: 'bold', color: '#cc6600' }}>{activeCase.status}</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div style={{ marginBottom: '15px' }}>
                <label style={{ fontWeight: 'bold', fontSize: '12px', display: 'block', marginBottom: '5px' }}>Raw Clinical Record (Scrubbed Target Area):</label>
                <div style={{ border: '1px solid #ccc', padding: '12px', fontSize: '13px', backgroundColor: '#fcfcfc', lineHeight: '1.4', maxHeight: '180px', overflowY: 'auto' }}>
                    {activeCase.raw_clinical_note}
                </div>
            </div>

            <div style={{ marginBottom: '25px' }}>
                <label style={{ fontWeight: 'bold', fontSize: '12px', display: 'block', marginBottom: '5px' }}>AI Extracted Taxonomy Targets:</label>
                {activeCase.extracted_codes && activeCase.extracted_codes.length > 0 ? (
                    activeCase.extracted_codes.map((item, idx) => (
                        <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', border: '1px solid #b3e5fc', backgroundColor: '#e1f5fe', padding: '10px', marginTop: '5px' }}>
                            <div>
                                <span style={{ backgroundColor: '#0288d1', color: '#fff', padding: '2px 6px', fontWeight: 'bold', fontSize: '12px', marginRight: '8px' }}>
                                    ICD-11: {item.code}
                                </span>
                                <span style={{ fontWeight: 'bold', fontSize: '13px' }}>{item.title}</span>
                            </div>
                            <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#0288d1' }}>
                                Confidence: {(item.confidence_score * 100).toFixed(1)}%
                            </div>
                        </div>
                    ))
                ) : (
                    <div style={{ padding: '10px', border: '1px dashed #aaa', color: '#777', fontSize: '12px', backgroundColor: '#fafafa' }}>
                        ⏳ No extracted keys confirmed. Pipeline execution status: [PENDING_AI]
                    </div>
                )}
            </div>

            <div style={{ display: 'flex', gap: '10px', borderTop: '1px solid #ddd', paddingTop: '15px' }}>
                <button
                    onClick={() => updateStatus('ARCHIVED')}
                    disabled={activeCase.status === 'ARCHIVED'}
                    style={{ flex: 1, padding: '10px', cursor: activeCase.status === 'ARCHIVED' ? 'not-allowed' : 'pointer', backgroundColor: '#4caf50', color: '#fff', border: 'none', fontWeight: 'bold' }}
                >
                    ✓ Commit Matching Mapping
                </button>
                <button
                    onClick={() => updateStatus('PENDING_HITL')}
                    disabled={activeCase.status === 'PENDING_HITL'}
                    style={{ flex: 1, padding: '10px', cursor: activeCase.status === 'PENDING_HITL' ? 'not-allowed' : 'pointer', backgroundColor: '#ff9800', color: '#fff', border: 'none', fontWeight: 'bold' }}
                >
                    ⚠️ Escalate Back to Queue
                </button>
            </div>
        </div>
    );
}