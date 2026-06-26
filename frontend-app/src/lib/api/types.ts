export type RegulationFamily = "battery" | "reach" | "rohs" | "weee" | "other";
export type FindingStatus = "red" | "amber" | "green";
export type AlertChannel = "sms" | "whatsapp" | "email";
export type AlertDeliveryStatus = "queued" | "sent" | "delivered" | "failed";
export type RegulationStatus = "upcoming" | "due" | "past";
export type Language = "en" | "de";

export interface Company {
  id: string;
  name: string;
  markets: string[];
  contacts: { name: string; email: string; phone?: string }[];
  preferredChannel: AlertChannel;
  preferredLanguage: Language;
}

export interface Product {
  id: string;
  companyId: string;
  name: string;
  category: string;
  batteryType?: string;
  substances: string[];
  markets: string[];
}

export interface RegulationArticle {
  ref: string; // e.g. "Art. 77"
  title: string;
  deadline?: string; // ISO date
  description: string;
}

export interface Regulation {
  id: string;
  reference: string; // e.g. "EU 2023/1542"
  title: string;
  family: RegulationFamily;
  status: RegulationStatus;
  deadline?: string; // ISO date
  sourceUrls: string[]; // multiple possible after dedupe
  articles: RegulationArticle[];
  summary: string;
}

export interface Finding {
  id: string;
  companyId: string;
  productId: string;
  regulationId: string;
  articleRef?: string;
  status: FindingStatus;
  deadline?: string;
  gapDescription: string;
  recommendedFix: string;
  sourceUrls: string[];
  alertChannel: AlertChannel;
  alertSent: boolean;
  alertSentAt?: string;
  highRiskSubstance?: boolean;
}

export interface AlertRecord {
  id: string;
  findingId: string;
  companyId: string;
  productId: string;
  regulationId: string;
  channel: AlertChannel;
  language: Language;
  sentAt: string;
  deliveryStatus: AlertDeliveryStatus;
  messagePreview: string;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  kind: "rule_updated" | "gap_found" | "alert_sent" | "rule_added" | "finding_resolved";
  summary: string;
  refs?: { companyId?: string; productId?: string; regulationId?: string; findingId?: string };
}
