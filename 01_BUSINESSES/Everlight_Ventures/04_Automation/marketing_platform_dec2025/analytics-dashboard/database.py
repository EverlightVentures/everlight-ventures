"""
Database connection and query utilities for Streamlit analytics dashboard
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/everlight_dev')
engine = create_engine(DATABASE_URL)


def get_campaign_overview(project_slug: str, start_date: datetime, end_date: datetime) -> dict:
    """Get overview metrics for campaigns"""
    query = text("""
        WITH project AS (
            SELECT id FROM "Project" WHERE slug = :project_slug
        ),
        campaign_stats AS (
            SELECT
                COUNT(DISTINCT c.id) as total_campaigns,
                COUNT(DISTINCT c.id) FILTER (
                    WHERE c."sentAt" >= :start_date AND c."sentAt" <= :end_date
                ) as campaigns_this_period,
                COUNT(DISTINCT cr.id) as total_sent,
                COUNT(DISTINCT cr.id) FILTER (WHERE cr."openCount" > 0) as unique_opens,
                SUM(cr."openCount") as total_opens,
                SUM(cr."clickCount") as total_clicks,
                AVG(CASE WHEN c.status = 'SENT' THEN c."openRate" END) as avg_open_rate,
                AVG(CASE WHEN c.status = 'SENT' THEN c."clickRate" END) as avg_click_rate
            FROM "Campaign" c
            LEFT JOIN "CampaignRecipient" cr ON c.id = cr."campaignId"
            WHERE c."projectId" = (SELECT id FROM project)
                AND c.status = 'SENT'
                AND c."sentAt" IS NOT NULL
        )
        SELECT * FROM campaign_stats
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {
            'project_slug': project_slug,
            'start_date': start_date,
            'end_date': end_date
        }).fetchone()

        if result:
            return {
                'total_campaigns': result[0] or 0,
                'campaigns_this_month': result[1] or 0,
                'total_sent': result[2] or 0,
                'unique_opens': result[3] or 0,
                'total_opens': result[4] or 0,
                'total_clicks': result[5] or 0,
                'avg_open_rate': (result[6] or 0) * 100,
                'avg_click_rate': (result[7] or 0) * 100,
            }
        return {}


def get_campaign_performance(project_slug: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Get detailed performance metrics for each campaign"""
    query = text("""
        WITH project AS (
            SELECT id FROM "Project" WHERE slug = :project_slug
        ),
        campaign_metrics AS (
            SELECT
                c.id,
                c.name,
                c.subject,
                c."sentAt" as sent_at,
                c."utmSource" as utm_source,
                c."utmMedium" as utm_medium,
                c."utmCampaign" as utm_campaign,
                COUNT(DISTINCT cr.id) as recipients,
                COUNT(DISTINCT cr.id) FILTER (WHERE cr."openCount" > 0) as unique_opens,
                SUM(cr."openCount") as opens,
                COUNT(DISTINCT cr.id) FILTER (WHERE cr."clickCount" > 0) as unique_clickers,
                SUM(cr."clickCount") as clicks,
                COUNT(DISTINCT u.id) as unsubscribes,
                CASE
                    WHEN COUNT(DISTINCT cr.id) > 0
                    THEN CAST(COUNT(DISTINCT cr.id) FILTER (WHERE cr."openCount" > 0) AS FLOAT) / COUNT(DISTINCT cr.id)
                    ELSE 0
                END as open_rate,
                CASE
                    WHEN COUNT(DISTINCT cr.id) > 0
                    THEN CAST(COUNT(DISTINCT cr.id) FILTER (WHERE cr."clickCount" > 0) AS FLOAT) / COUNT(DISTINCT cr.id)
                    ELSE 0
                END as click_rate
            FROM "Campaign" c
            LEFT JOIN "CampaignRecipient" cr ON c.id = cr."campaignId"
            LEFT JOIN "Unsubscribe" u ON c.id = u."campaignId"
            WHERE c."projectId" = (SELECT id FROM project)
                AND c.status = 'SENT'
                AND c."sentAt" >= :start_date
                AND c."sentAt" <= :end_date
            GROUP BY c.id, c.name, c.subject, c."sentAt", c."utmSource", c."utmMedium", c."utmCampaign"
            ORDER BY c."sentAt" DESC
        )
        SELECT * FROM campaign_metrics
    """)

    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn, params={
            'project_slug': project_slug,
            'start_date': start_date,
            'end_date': end_date
        })
        return df


def get_top_links(project_slug: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Get top performing links across all campaigns"""
    query = text("""
        WITH project AS (
            SELECT id FROM "Project" WHERE slug = :project_slug
        )
        SELECT
            ec.url,
            COUNT(*) as clicks,
            COUNT(DISTINCT ec."recipientId") as unique_clickers,
            COUNT(DISTINCT cr."campaignId") as campaigns
        FROM "EmailClick" ec
        JOIN "CampaignRecipient" cr ON ec."recipientId" = cr.id
        JOIN "Campaign" c ON cr."campaignId" = c.id
        WHERE c."projectId" = (SELECT id FROM project)
            AND ec."clickedAt" >= :start_date
            AND ec."clickedAt" <= :end_date
        GROUP BY ec.url
        ORDER BY clicks DESC
        LIMIT 50
    """)

    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn, params={
            'project_slug': project_slug,
            'start_date': start_date,
            'end_date': end_date
        })
        return df


def get_subscriber_engagement(project_slug: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Get subscriber engagement levels"""
    query = text("""
        WITH project AS (
            SELECT id FROM "Project" WHERE slug = :project_slug
        ),
        contact_engagement AS (
            SELECT
                c.email,
                COUNT(DISTINCT cr.id) as campaigns_received,
                SUM(cr."openCount") as opens,
                SUM(cr."clickCount") as clicks,
                MAX(cr."lastOpenedAt") as last_opened,
                MAX(cr."lastClickedAt") as last_clicked,
                (SUM(cr."openCount") * 1.0 + SUM(cr."clickCount") * 2.0) as total_engagement,
                CASE
                    WHEN SUM(cr."openCount") + SUM(cr."clickCount") = 0 THEN 'Inactive'
                    WHEN (SUM(cr."openCount") * 1.0 + SUM(cr."clickCount") * 2.0) > 10 THEN 'Highly Engaged'
                    WHEN (SUM(cr."openCount") * 1.0 + SUM(cr."clickCount") * 2.0) > 3 THEN 'Engaged'
                    ELSE 'Low Engagement'
                END as engagement_level
            FROM "Contact" c
            JOIN "CampaignRecipient" cr ON c.id = cr."contactId"
            JOIN "Campaign" camp ON cr."campaignId" = camp.id
            WHERE c."projectId" = (SELECT id FROM project)
                AND camp."sentAt" >= :start_date
                AND camp."sentAt" <= :end_date
            GROUP BY c.id, c.email
        )
        SELECT * FROM contact_engagement
        ORDER BY total_engagement DESC
    """)

    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn, params={
            'project_slug': project_slug,
            'start_date': start_date,
            'end_date': end_date
        })
        return df


def get_activity_timeline(project_slug: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Get activity timeline"""
    query = text("""
        WITH project AS (
            SELECT id FROM "Project" WHERE slug = :project_slug
        )
        SELECT
            a.type,
            a."createdAt" as created_at,
            a.metadata
        FROM "Activity" a
        WHERE a."projectId" = (SELECT id FROM project)
            AND a."createdAt" >= :start_date
            AND a."createdAt" <= :end_date
        ORDER BY a."createdAt" DESC
    """)

    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn, params={
            'project_slug': project_slug,
            'start_date': start_date,
            'end_date': end_date
        })
        return df


def get_unsubscribe_reasons(project_slug: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Get unsubscribe reasons and stats"""
    query = text("""
        WITH project AS (
            SELECT id FROM "Project" WHERE slug = :project_slug
        )
        SELECT
            u.reason,
            COUNT(*) as count,
            c.name as campaign_name
        FROM "Unsubscribe" u
        LEFT JOIN "Campaign" c ON u."campaignId" = c.id
        WHERE u."projectId" = (SELECT id FROM project)
            AND u."unsubscribedAt" >= :start_date
            AND u."unsubscribedAt" <= :end_date
        GROUP BY u.reason, c.name
        ORDER BY count DESC
    """)

    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn, params={
            'project_slug': project_slug,
            'start_date': start_date,
            'end_date': end_date
        })
        return df


def get_email_client_stats(project_slug: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Get email client usage statistics"""
    query = text("""
        WITH project AS (
            SELECT id FROM "Project" WHERE slug = :project_slug
        ),
        client_stats AS (
            SELECT
                CASE
                    WHEN eo."userAgent" LIKE '%Gmail%' THEN 'Gmail'
                    WHEN eo."userAgent" LIKE '%Outlook%' THEN 'Outlook'
                    WHEN eo."userAgent" LIKE '%Apple Mail%' THEN 'Apple Mail'
                    WHEN eo."userAgent" LIKE '%Yahoo%' THEN 'Yahoo Mail'
                    WHEN eo."userAgent" LIKE '%Thunderbird%' THEN 'Thunderbird'
                    WHEN eo."userAgent" LIKE '%Mobile%' OR eo."userAgent" LIKE '%iPhone%' OR eo."userAgent" LIKE '%Android%' THEN 'Mobile'
                    ELSE 'Other'
                END as email_client,
                COUNT(*) as count
            FROM "EmailOpen" eo
            JOIN "CampaignRecipient" cr ON eo."recipientId" = cr.id
            JOIN "Campaign" c ON cr."campaignId" = c.id
            WHERE c."projectId" = (SELECT id FROM project)
                AND eo."openedAt" >= :start_date
                AND eo."openedAt" <= :end_date
            GROUP BY email_client
        )
        SELECT
            email_client,
            count,
            ROUND(count * 100.0 / SUM(count) OVER (), 2) as percentage
        FROM client_stats
        ORDER BY count DESC
    """)

    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn, params={
            'project_slug': project_slug,
            'start_date': start_date,
            'end_date': end_date
        })
        return df


def get_hourly_engagement(project_slug: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Get engagement by hour of day"""
    query = text("""
        WITH project AS (
            SELECT id FROM "Project" WHERE slug = :project_slug
        ),
        hourly_data AS (
            SELECT EXTRACT(HOUR FROM eo."openedAt") as hour, COUNT(*) as opens
            FROM "EmailOpen" eo
            JOIN "CampaignRecipient" cr ON eo."recipientId" = cr.id
            JOIN "Campaign" c ON cr."campaignId" = c.id
            WHERE c."projectId" = (SELECT id FROM project)
                AND eo."openedAt" >= :start_date
                AND eo."openedAt" <= :end_date
            GROUP BY EXTRACT(HOUR FROM eo."openedAt")

            UNION ALL

            SELECT EXTRACT(HOUR FROM ec."clickedAt") as hour, COUNT(*) as clicks
            FROM "EmailClick" ec
            JOIN "CampaignRecipient" cr ON ec."recipientId" = cr.id
            JOIN "Campaign" c ON cr."campaignId" = c.id
            WHERE c."projectId" = (SELECT id FROM project)
                AND ec."clickedAt" >= :start_date
                AND ec."clickedAt" <= :end_date
            GROUP BY EXTRACT(HOUR FROM ec."clickedAt")
        )
        SELECT
            hour::integer,
            SUM(opens) as events
        FROM hourly_data
        GROUP BY hour
        ORDER BY hour
    """)

    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn, params={
            'project_slug': project_slug,
            'start_date': start_date,
            'end_date': end_date
        })
        return df
