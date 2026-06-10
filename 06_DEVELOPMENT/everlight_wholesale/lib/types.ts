export type LeadStatus =
  | "new"
  | "contacted"
  | "negotiating"
  | "verbal_agreement"
  | "contract_sent"
  | "signed"
  | "buyer_blast"
  | "contract_assigned"
  | "title_hold"
  | "closed"
  | "funds_received"
  | "dead";

export interface Lead {
  id: string;
  owner_name: string;
  address: string;
  city: string;
  state: string;
  zip?: string;
  email?: string;
  owner_email?: string;
  phone?: string;
  owner_phone?: string;
  estimated_arv?: number;
  arv?: number;
  beds?: number | string;
  baths?: number | string;
  sqft?: number | string;
  year_built?: number | string;
  last_sale_price?: number;
  last_sale_date?: string;
  lead_type?: string;
  detected_distress?: string;
  status: LeadStatus | string;
  outreach_count?: number;
  sequence_step?: number;
  last_outreach?: string;
  first_contacted?: string;
  reply_received?: boolean;
  offer_amount?: number | string;
  assigned_title_company?: string;
  source?: string;
  created_at?: string;
  listing_url?: string;
  owner_classification?: "individual" | "institutional";
  conversation?: Array<{
    role: string;
    agent_name?: string;
    agent_email?: string;
    channel?: string;
    direction?: "outbound" | "inbound";
    to?: string;
    from?: string;
    subject?: string;
    message: string;
    message_html?: string;
    step?: number;
    timestamp: string;
    reconstructed?: boolean;
  }>;
  skip_traced_at?: string;
  skip_trace_source?: string;
}

export interface Buyer {
  name: string;
  company?: string;
  email: string;
  phone?: string;
  city?: string;
  state: string;
  market?: string;
  buy_criteria?: string;
  deals_sent?: number;
  deals_closed?: number;
  status?: string;
  responded?: boolean;
  on_deal_list?: boolean;
  added_date?: string;
  last_outreach?: string;
}

export interface TitleCompany {
  id?: string;
  rank: number;
  primary: boolean;
  name: string;
  phone?: string;
  email?: string;
  website?: string;
  contact?: string;
  handles_assignments?: boolean;
  investor_friendly?: string;
  deals_closed?: number;
  notes?: string;
  state?: string;
  market?: string;
  closing_type?: string;
}

export interface StateTitleEntry {
  market?: string;
  preferred_closer_id?: string;
  closing_type?: string;
  companies: TitleCompany[];
}

export interface DealEvent {
  id: string;
  ts: string;
  type: string;           // wholesale_lead_new | wholesale_reply | magnet_click | ...
  outcome?: string;
  payload?: Record<string, unknown>;
}

export interface KPIs {
  total: number;
  contactable: number;
  in_sequence: number;
  replied: number;
  closed: number;
  by_state: Record<string, { total: number; contactable: number; in_seq: number; replied: number }>;
  clicks_24h: number;
  new_today: number;
}
