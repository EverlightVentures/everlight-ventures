'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@everlight/ui';

export default function SendCampaignPage() {
  const router = useRouter();
  const params = useParams();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [campaign, setCampaign] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [campaignRes, statsRes] = await Promise.all([
          fetch(`/api/projects/${params.slug}/campaigns/${params.id}`),
          fetch(`/api/projects/${params.slug}/campaigns/${params.id}/preview`),
        ]);

        if (campaignRes.ok) {
          const data = await campaignRes.json();
          setCampaign(data.campaign);
        }

        if (statsRes.ok) {
          const data = await statsRes.json();
          setStats(data);
        }
      } catch (err) {
        console.error('Failed to fetch campaign data:', err);
      }
    }

    fetchData();
  }, [params.slug, params.id]);

  async function handleSend() {
    if (!confirm(`Send this campaign to ${stats?.subscribedCount || 0} subscribers?`)) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/projects/${params.slug}/campaigns/${params.id}/send`,
        { method: 'POST' }
      );

      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.error || 'Failed to send campaign');
      }

      alert('Campaign sent successfully!');
      router.push(`/projects/${params.slug}/campaigns`);
      router.refresh();
    } catch (err: any) {
      setError(err.message);
      setIsLoading(false);
    }
  }

  if (!campaign || !stats) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8">
        <Card>
          <CardContent className="py-8 text-center">
            Loading campaign details...
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <Card>
        <CardHeader>
          <CardTitle>Send Campaign: {campaign.name}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h3 className="font-semibold">Subject</h3>
            <p className="text-gray-600">{campaign.subject}</p>
          </div>

          <div>
            <h3 className="font-semibold">Recipients</h3>
            <p className="text-gray-600">
              {stats.subscribedCount} subscribed contacts
            </p>
          </div>

          <div className="rounded-md border p-4">
            <h3 className="mb-2 font-semibold">Preview</h3>
            <div
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: campaign.htmlContent }}
            />
          </div>

          {error && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">
              {error}
            </div>
          )}

          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              className="flex-1"
              onClick={() => router.back()}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              type="button"
              className="flex-1"
              onClick={handleSend}
              disabled={isLoading || stats.subscribedCount === 0}
            >
              {isLoading ? 'Sending...' : `Send to ${stats.subscribedCount} Recipients`}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
