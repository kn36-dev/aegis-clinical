import React from 'react';
import type { PatientCase } from '../App';

interface DashboardProps {
    cases: PatientCase[];
    selectedCaseId: string | null;
    onSelectCase: (id: string) => void;
}

export default function Dashboard({ cases, selectedCaseId, onSelectCase }: DashboardProps) {
    return (
        <div>
            <h3 style={{ margin: '0 0 15px 0', borderBottom: '1px dashed #333', paddingBottom: '5px' }}>
                📋 INGRESS PIPELINE QUEUE
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {cases.map((c) => {
                    const isSelected = c.case_id === selectedCaseId;
                    return (
                        <div
                            key={c.case_id}
                            onClick={() => onSelectCase(c.case_id)}
                            style={{
                                padding: '12px',
                                border: isSelected ? '2px solid #0066cc' : '1px solid #ddd',
                                backgroundColor: isSelected ? '#f0f7ff' : '#fafafa',
                                cursor: 'pointer',
                                transition: 'background-color 0.2s'
                            }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                <span style={{ fontWeight: 'bold', fontSize: '13px' }}>ID: {c.case_id.slice(0, 8)}...</span>
                                <span style={{
                                    fontSize: '11px',
                                    padding: '2px 6px',
                                    backgroundColor: c.status === 'PENDING_HITL' ? '#ffe0b2' : c.status === 'PENDING_AI' ? '#b3e5fc' : '#c8e6c9',
                                    color: '#333',
                                    fontWeight: 'bold'
                                }}>
                                    {c.status}
                                </span>
                            </div>
                            <div style={{ fontSize: '11px', color: '#666' }}>
                                Ingress: {c.ingress_timestamp}
                            </div>
                            <div style={{ fontSize: '12px', marginTop: '6px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: '#444' }}>
                                {c.raw_clinical_note}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}