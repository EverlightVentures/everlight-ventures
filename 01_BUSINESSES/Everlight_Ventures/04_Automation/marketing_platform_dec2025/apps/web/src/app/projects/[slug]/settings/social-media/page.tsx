'use client';

import { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@everlight/ui';
import { Instagram, Facebook, Video, CheckCircle2, XCircle, Clock } from 'lucide-react';

interface SocialAccount {
  id: string;
  platform: 'INSTAGRAM' | 'FACEBOOK' | 'TIKTOK';
  platformUsername: string | null;
  displayName: string | null;
  status: 'CONNECTED' | 'DISCONNECTED' | 'TOKEN_EXPIRED' | 'ERROR';
  lastSyncedAt: string | null;
}

export default function SocialMediaSettingsPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    // Show success message if redirected from OAuth
    if (searchParams.get('success') === 'true') {
      setSuccessMessage('Social media account connected successfully!');
      setTimeout(() => setSuccessMessage(''), 5000);
    }

    fetchAccounts();
  }, []);

  async function fetchAccounts() {
    try {
      const response = await fetch(`/api/projects/${params.slug}/social/accounts`);
      if (response.ok) {
        const data = await response.json();
        setAccounts(data.accounts || []);
      }
    } catch (error) {
      console.error('Failed to fetch accounts:', error);
    } finally {
      setIsLoading(false);
    }
  }

  async function connectFacebook() {
    window.location.href = `/api/social/facebook/connect?projectSlug=${params.slug}`;
  }

  async function disconnectAccount(accountId: string) {
    if (!confirm('Are you sure you want to disconnect this account?')) {
      return;
    }

    try {
      const response = await fetch(`/api/projects/${params.slug}/social/accounts/${accountId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        fetchAccounts();
      }
    } catch (error) {
      console.error('Failed to disconnect account:', error);
    }
  }

  const getAccountIcon = (platform: string) => {
    switch (platform) {
      case 'INSTAGRAM':
        return <Instagram className="w-5 h-5" />;
      case 'FACEBOOK':
        return <Facebook className="w-5 h-5" />;
      case 'TIKTOK':
        return <Video className="w-5 h-5" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'CONNECTED':
        return (
          <span className="flex items-center gap-1 text-green-600 text-sm">
            <CheckCircle2 className="w-4 h-4" />
            Connected
          </span>
        );
      case 'TOKEN_EXPIRED':
        return (
          <span className="flex items-center gap-1 text-yellow-600 text-sm">
            <Clock className="w-4 h-4" />
            Token Expired
          </span>
        );
      case 'ERROR':
      case 'DISCONNECTED':
        return (
          <span className="flex items-center gap-1 text-red-600 text-sm">
            <XCircle className="w-4 h-4" />
            Disconnected
          </span>
        );
      default:
        return null;
    }
  };

  const instagramAccount = accounts.find((a) => a.platform === 'INSTAGRAM');
  const facebookAccount = accounts.find((a) => a.platform === 'FACEBOOK');
  const tiktokAccount = accounts.find((a) => a.platform === 'TIKTOK');

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Social Media Accounts</h1>
        <p className="text-muted-foreground mt-1">
          Connect your social media accounts to enable cross-posting
        </p>
      </div>

      {successMessage && (
        <div className="mb-6 rounded-md bg-green-50 p-4 text-green-800">
          {successMessage}
        </div>
      )}

      <div className="space-y-4">
        {/* Instagram */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-purple-600 via-pink-600 to-orange-600">
                  <Instagram className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold">Instagram</h3>
                  {instagramAccount ? (
                    <>
                      <p className="text-sm text-muted-foreground">
                        @{instagramAccount.platformUsername || 'Unknown'}
                      </p>
                      <div className="mt-1">{getStatusBadge(instagramAccount.status)}</div>
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground">Not connected</p>
                  )}
                </div>
              </div>
              <div>
                {instagramAccount ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => disconnectAccount(instagramAccount.id)}
                  >
                    Disconnect
                  </Button>
                ) : (
                  <Button size="sm" onClick={connectFacebook} disabled={!!facebookAccount}>
                    Connect
                  </Button>
                )}
              </div>
            </div>
            {!instagramAccount && (
              <div className="mt-4 rounded-md bg-blue-50 p-3 text-sm text-blue-800">
                <p className="font-medium">ℹ️ Instagram requires Facebook connection</p>
                <p className="mt-1 text-xs">
                  Connect your Facebook Page first. Instagram Business Account will be detected automatically.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Facebook */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-600">
                  <Facebook className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold">Facebook</h3>
                  {facebookAccount ? (
                    <>
                      <p className="text-sm text-muted-foreground">
                        {facebookAccount.displayName || facebookAccount.platformUsername}
                      </p>
                      <div className="mt-1">{getStatusBadge(facebookAccount.status)}</div>
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground">Not connected</p>
                  )}
                </div>
              </div>
              <div>
                {facebookAccount ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => disconnectAccount(facebookAccount.id)}
                  >
                    Disconnect
                  </Button>
                ) : (
                  <Button size="sm" onClick={connectFacebook}>
                    Connect
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* TikTok */}
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-black">
                  <Video className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold">TikTok</h3>
                  {tiktokAccount ? (
                    <>
                      <p className="text-sm text-muted-foreground">
                        @{tiktokAccount.platformUsername || 'Unknown'}
                      </p>
                      <div className="mt-1">{getStatusBadge(tiktokAccount.status)}</div>
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground">Not connected</p>
                  )}
                </div>
              </div>
              <div>
                <Button size="sm" disabled>
                  Coming Soon
                </Button>
              </div>
            </div>
            <div className="mt-4 rounded-md bg-yellow-50 p-3 text-sm text-yellow-800">
              <p className="font-medium">⏳ TikTok integration coming soon</p>
              <p className="mt-1 text-xs">
                TikTok API requires developer approval. This feature will be available once approved.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Setup Instructions */}
      <Card className="mt-8">
        <CardHeader>
          <CardTitle>📝 Setup Instructions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h4 className="font-medium mb-2">Before connecting Facebook/Instagram:</h4>
            <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
              <li>Create a Facebook App at developers.facebook.com</li>
              <li>Add Instagram Graph API product</li>
              <li>Request permissions: pages_manage_posts, instagram_basic, instagram_content_publish</li>
              <li>Add your app credentials to .env (FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)</li>
              <li>Ensure your Instagram account is a Business/Creator account linked to a Facebook Page</li>
            </ol>
          </div>

          <div className="pt-4 border-t">
            <h4 className="font-medium mb-2">After connecting:</h4>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              <li>Create a new campaign and enable "Social Media Distribution"</li>
              <li>Upload your video or image content</li>
              <li>Select which platforms to post to</li>
              <li>Click "Create & Distribute" to send everywhere at once!</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
