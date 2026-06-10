"""
Everlight Ventures - Marketing Analytics Dashboard
Advanced Streamlit dashboard for analyzing email campaign metrics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import (
    get_campaign_overview,
    get_campaign_performance,
    get_top_links,
    get_subscriber_engagement,
    get_activity_timeline,
    get_unsubscribe_reasons,
    get_email_client_stats,
    get_hourly_engagement,
)

# Page configuration
st.set_page_config(
    page_title="Everlight Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #2563eb;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .big-number {
        font-size: 3rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar - Filters
st.sidebar.title("🎛️ Filters")

# Project selector
project_filter = st.sidebar.text_input("Project Slug", value="demo-project")

# Date range selector
date_range = st.sidebar.date_input(
    "Date Range",
    value=(datetime.now() - timedelta(days=30), datetime.now()),
    max_value=datetime.now(),
)

# Campaign type filter
campaign_status = st.sidebar.multiselect(
    "Campaign Status",
    options=["DRAFT", "SENDING", "SENT", "FAILED"],
    default=["SENT"],
)

# Refresh button
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# Main Dashboard
st.markdown('<h1 class="main-header">📊 Marketing Analytics Dashboard</h1>', unsafe_allow_html=True)
st.markdown(f"**Project:** {project_filter} | **Date Range:** {date_range[0]} to {date_range[1]}")

# Fetch data
with st.spinner("Loading analytics..."):
    overview = get_campaign_overview(project_filter, date_range[0], date_range[1])
    campaigns = get_campaign_performance(project_filter, date_range[0], date_range[1])
    top_links = get_top_links(project_filter, date_range[0], date_range[1])
    engagement = get_subscriber_engagement(project_filter, date_range[0], date_range[1])
    activity = get_activity_timeline(project_filter, date_range[0], date_range[1])

# Overview Metrics
st.header("📈 Overview Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Campaigns",
        value=overview.get('total_campaigns', 0),
        delta=f"+{overview.get('campaigns_this_month', 0)} this month"
    )

with col2:
    st.metric(
        label="Total Emails Sent",
        value=f"{overview.get('total_sent', 0):,}",
        delta=f"{overview.get('avg_open_rate', 0):.1f}% avg open rate"
    )

with col3:
    st.metric(
        label="Total Opens",
        value=f"{overview.get('total_opens', 0):,}",
        delta=f"{overview.get('unique_opens', 0):,} unique"
    )

with col4:
    st.metric(
        label="Total Clicks",
        value=f"{overview.get('total_clicks', 0):,}",
        delta=f"{overview.get('avg_click_rate', 0):.1f}% avg CTR"
    )

st.divider()

# Campaign Performance Table
st.header("📧 Campaign Performance")

if not campaigns.empty:
    # Add calculated columns
    campaigns['open_rate_pct'] = (campaigns['open_rate'] * 100).round(2)
    campaigns['click_rate_pct'] = (campaigns['click_rate'] * 100).round(2)

    # Display table with formatting
    st.dataframe(
        campaigns[[
            'name', 'subject', 'sent_at', 'recipients',
            'opens', 'clicks', 'open_rate_pct', 'click_rate_pct', 'unsubscribes'
        ]].rename(columns={
            'name': 'Campaign Name',
            'subject': 'Subject',
            'sent_at': 'Sent Date',
            'recipients': 'Recipients',
            'opens': 'Opens',
            'clicks': 'Clicks',
            'open_rate_pct': 'Open Rate %',
            'click_rate_pct': 'Click Rate %',
            'unsubscribes': 'Unsubscribes',
        }),
        use_container_width=True,
        hide_index=True,
    )

    # Performance comparison chart
    st.subheader("📊 Campaign Comparison")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Open Rate %',
        x=campaigns['name'],
        y=campaigns['open_rate_pct'],
        marker_color='lightblue'
    ))

    fig.add_trace(go.Bar(
        name='Click Rate %',
        x=campaigns['name'],
        y=campaigns['click_rate_pct'],
        marker_color='darkblue'
    ))

    fig.update_layout(
        barmode='group',
        title='Campaign Performance Comparison',
        xaxis_title='Campaign',
        yaxis_title='Rate (%)',
        height=400,
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No campaigns found for the selected date range.")

st.divider()

# Top Performing Links
st.header("🔗 Top Performing Links")

col1, col2 = st.columns([2, 1])

with col1:
    if not top_links.empty:
        # Bar chart of top links
        fig = px.bar(
            top_links.head(10),
            x='clicks',
            y='url',
            orientation='h',
            title='Top 10 Clicked Links',
            labels={'clicks': 'Total Clicks', 'url': 'URL'},
            color='clicks',
            color_continuous_scale='Blues',
        )
        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No link click data available.")

with col2:
    if not top_links.empty:
        st.subheader("📋 Link Details")
        st.dataframe(
            top_links[['url', 'clicks', 'unique_clickers']].rename(columns={
                'url': 'URL',
                'clicks': 'Total Clicks',
                'unique_clickers': 'Unique Users',
            }),
            use_container_width=True,
            hide_index=True,
        )

st.divider()

# Subscriber Engagement Analysis
st.header("👥 Subscriber Engagement")

if not engagement.empty:
    col1, col2 = st.columns(2)

    with col1:
        # Engagement distribution
        engagement_levels = engagement['engagement_level'].value_counts()
        fig = px.pie(
            values=engagement_levels.values,
            names=engagement_levels.index,
            title='Subscriber Engagement Distribution',
            color_discrete_sequence=px.colors.sequential.RdBu,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Top engaged subscribers
        st.subheader("🌟 Most Engaged Subscribers")
        top_engaged = engagement.nlargest(10, 'total_engagement')
        st.dataframe(
            top_engaged[['email', 'opens', 'clicks', 'total_engagement']].rename(columns={
                'email': 'Email',
                'opens': 'Opens',
                'clicks': 'Clicks',
                'total_engagement': 'Engagement Score',
            }),
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("No subscriber engagement data available.")

st.divider()

# Activity Timeline
st.header("⏱️ Activity Timeline")

if not activity.empty:
    # Group by hour and activity type
    activity_by_hour = activity.groupby([
        pd.Grouper(key='created_at', freq='H'),
        'type'
    ]).size().reset_index(name='count')

    fig = px.line(
        activity_by_hour,
        x='created_at',
        y='count',
        color='type',
        title='Activity Over Time (by Hour)',
        labels={'created_at': 'Time', 'count': 'Events', 'type': 'Activity Type'},
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Activity breakdown
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Activity Breakdown")
        activity_counts = activity['type'].value_counts()
        st.dataframe(
            pd.DataFrame({
                'Activity Type': activity_counts.index,
                'Count': activity_counts.values,
            }),
            use_container_width=True,
            hide_index=True,
        )

    with col2:
        st.subheader("🕐 Peak Activity Hours")
        hourly_engagement = get_hourly_engagement(project_filter, date_range[0], date_range[1])
        if not hourly_engagement.empty:
            fig = px.bar(
                hourly_engagement,
                x='hour',
                y='events',
                title='Engagement by Hour of Day',
                labels={'hour': 'Hour (24h)', 'events': 'Total Events'},
                color='events',
                color_continuous_scale='Viridis',
            )
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No activity data available.")

st.divider()

# Advanced Analytics
st.header("🔬 Advanced Analytics")

tab1, tab2, tab3 = st.tabs(["📉 Unsubscribe Analysis", "📱 Email Client Stats", "📥 Export Data"])

with tab1:
    unsubscribes = get_unsubscribe_reasons(project_filter, date_range[0], date_range[1])
    if not unsubscribes.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Unsubscribe Reasons")
            st.dataframe(unsubscribes, use_container_width=True, hide_index=True)

        with col2:
            st.subheader("Unsubscribe Rate by Campaign")
            if not campaigns.empty:
                campaigns_with_unsub = campaigns[campaigns['unsubscribes'] > 0]
                if not campaigns_with_unsub.empty:
                    fig = px.bar(
                        campaigns_with_unsub,
                        x='name',
                        y='unsubscribes',
                        title='Unsubscribes by Campaign',
                        labels={'name': 'Campaign', 'unsubscribes': 'Unsubscribes'},
                        color='unsubscribes',
                        color_continuous_scale='Reds',
                    )
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No unsubscribe data available.")

with tab2:
    email_clients = get_email_client_stats(project_filter, date_range[0], date_range[1])
    if not email_clients.empty:
        col1, col2 = st.columns(2)

        with col1:
            fig = px.pie(
                email_clients,
                values='count',
                names='email_client',
                title='Email Client Distribution',
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.dataframe(
                email_clients.rename(columns={
                    'email_client': 'Email Client',
                    'count': 'Opens',
                    'percentage': 'Percentage',
                }),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("No email client data available.")

with tab3:
    st.subheader("📥 Export Analytics Data")

    col1, col2, col3 = st.columns(3)

    with col1:
        if not campaigns.empty:
            csv = campaigns.to_csv(index=False)
            st.download_button(
                label="📊 Download Campaign Data (CSV)",
                data=csv,
                file_name=f"campaigns_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )

    with col2:
        if not engagement.empty:
            csv = engagement.to_csv(index=False)
            st.download_button(
                label="👥 Download Engagement Data (CSV)",
                data=csv,
                file_name=f"engagement_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )

    with col3:
        if not top_links.empty:
            csv = top_links.to_csv(index=False)
            st.download_button(
                label="🔗 Download Link Data (CSV)",
                data=csv,
                file_name=f"links_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>Everlight Ventures Marketing Analytics Dashboard</p>
    <p style='font-size: 0.8rem;'>Data refreshes automatically. Last updated: {}</p>
</div>
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')), unsafe_allow_html=True)
