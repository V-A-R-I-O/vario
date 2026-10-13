import React from 'react';
import { DataCard, NotFound } from './messages';
import type { KeyValue, BotMessageData } from './types';

export interface AdmissionsStatusProps {
  applicationId: string;
  status: string;
  nextStep: string;
  program?: string;
  applicantName?: string;
  feeStatus?: string;
}

/**
 * Admissions Status Card (slice-24).
 * Composes the shared DataCard component to display an applicant's
 * application ID, status badge/value, next step, and optional details.
 */
export function AdmissionsStatusCard({
  applicationId,
  status,
  nextStep,
  program,
  applicantName,
  feeStatus,
}: AdmissionsStatusProps) {
  const rows: KeyValue[] = [
    { label: 'Application ID', value: applicationId },
    { label: 'Status', value: status },
    { label: 'Next Step', value: nextStep },
  ];

  if (applicantName) {
    rows.push({ label: 'Applicant', value: applicantName });
  }

  if (program) {
    rows.push({ label: 'Program', value: program });
  }

  if (feeStatus) {
    rows.push({ label: 'Fee Status', value: feeStatus });
  }

  return (
    <DataCard
      title={`Application ${applicationId} Status`}
      rows={rows}
    />
  );
}

/**
 * Admissions Not Found Card (slice-24 / FR-17).
 * Composes the shared NotFound component with a graceful warning
 * and suggested next step for unknown application IDs.
 */
export function AdmissionsNotFoundCard({
  applicationId,
  suggestedNextStep,
}: {
  applicationId?: string;
  suggestedNextStep?: string;
}) {
  const suggestion =
    suggestedNextStep ||
    'Please verify your application ID or contact admissions@org.example.com.';
  const text = applicationId
    ? `Application ${applicationId} not found. Suggested next step: ${suggestion}`
    : `Application not found. Suggested next step: ${suggestion}`;

  return <NotFound text={text} />;
}

/**
 * Helper to transform status slots/content into BotMessageData for BotMessage.
 */
export function createAdmissionsStatusMessage(data: AdmissionsStatusProps): BotMessageData {
  const rows: KeyValue[] = [
    { label: 'Application ID', value: data.applicationId },
    { label: 'Status', value: data.status },
    { label: 'Next Step', value: data.nextStep },
  ];

  if (data.applicantName) rows.push({ label: 'Applicant', value: data.applicantName });
  if (data.program) rows.push({ label: 'Program', value: data.program });
  if (data.feeStatus) rows.push({ label: 'Fee Status', value: data.feeStatus });

  return {
    type: 'data_card',
    title: `Application ${data.applicationId} Status`,
    rows,
  };
}

export function createAdmissionsNotFoundMessage(
  applicationId?: string,
  suggestedNextStep?: string
): BotMessageData {
  const suggestion =
    suggestedNextStep ||
    'Please verify your application ID or contact admissions@org.example.com.';
  const text = applicationId
    ? `Application ${applicationId} not found. Suggested next step: ${suggestion}`
    : `Application not found. Suggested next step: ${suggestion}`;

  return {
    type: 'not_found',
    text,
  };
}
