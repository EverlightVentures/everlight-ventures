'use client';

import { useState, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useDropzone } from 'react-dropzone';
import { Button, Input, Label, Card, CardContent, CardHeader, CardTitle } from '@everlight/ui';
import { Upload, X, Image as ImageIcon, Video, Instagram, Facebook } from 'lucide-react';

interface UploadedMedia {
  id: string;
  type: 'IMAGE' | 'VIDEO';
  url: string;
  thumbnailUrl?: string;
  fileName: string;
  fileSize: number;
}

export default function NewCampaignPage() {
  const router = useRouter();
  const params = useParams();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedMedia, setUploadedMedia] = useState<UploadedMedia[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  // Social media state
  const [enableSocial, setEnableSocial] = useState(true);
  const [selectedPlatforms, setSelectedPlatforms] = useState({
    instagram: true,
    facebook: true,
    tiktok: false,
  });
  const [socialCaption, setSocialCaption] = useState('');
  const [hashtags, setHashtags] = useState('');

  // Handle file upload
  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setIsUploading(true);
    setError(null);

    try {
      for (const file of acceptedFiles) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('platform', 'INSTAGRAM'); // Default platform for validation

        const response = await fetch(`/api/projects/${params.slug}/media/upload`, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const result = await response.json();
          throw new Error(result.error || 'Failed to upload media');
        }

        const { asset } = await response.json();
        setUploadedMedia((prev) => [...prev, asset]);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  }, [params.slug]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.webp'],
      'video/*': ['.mp4', '.mov', '.webm'],
    },
    maxSize: 100 * 1024 * 1024, // 100MB
  });

  // Remove uploaded media
  const removeMedia = (id: string) => {
    setUploadedMedia((prev) => prev.filter((m) => m.id !== id));
  };

  // Auto-generate social caption from email subject
  const handleSubjectChange = (subject: string) => {
    if (!socialCaption) {
      setSocialCaption(subject);
    }
  };

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    const formData = new FormData(event.currentTarget);

    const data = {
      name: formData.get('name') as string,
      subject: formData.get('subject') as string,
      htmlContent: formData.get('htmlContent') as string,
      textContent: formData.get('textContent') as string,
      utmSource: formData.get('utmSource') as string,
      utmMedium: formData.get('utmMedium') as string,
      utmCampaign: formData.get('utmCampaign') as string,
      utmContent: formData.get('utmContent') as string,
      // Social media fields
      enableSocialPosting: enableSocial,
      socialCaption: socialCaption,
      socialHashtags: hashtags.split(' ').filter(tag => tag.startsWith('#')),
    };

    try {
      const response = await fetch(`/api/projects/${params.slug}/campaigns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.error || 'Failed to create campaign');
      }

      const { campaign } = await response.json();
      router.push(`/projects/${params.slug}/campaigns/${campaign.id}`);
      router.refresh();
    } catch (err: any) {
      setError(err.message);
      setIsLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Create Content Campaign</h1>
        <p className="text-muted-foreground mt-1">
          Drop your videos or images, write your content, and distribute everywhere at once.
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-6">
        {/* Media Upload Section */}
        <Card>
          <CardHeader>
            <CardTitle>📹 Upload Your Content</CardTitle>
          </CardHeader>
          <CardContent>
            {/* Dropzone */}
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragActive
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <input {...getInputProps()} />
              <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
              {isDragActive ? (
                <p className="text-lg font-medium">Drop your files here...</p>
              ) : (
                <>
                  <p className="text-lg font-medium mb-1">
                    Drop AI videos or ebook images here
                  </p>
                  <p className="text-sm text-muted-foreground">
                    or click to browse (Images: JPG, PNG, WebP | Videos: MP4, MOV, WebM)
                  </p>
                  <p className="text-xs text-muted-foreground mt-2">Max 100MB per file</p>
                </>
              )}
            </div>

            {/* Uploaded Media Preview */}
            {uploadedMedia.length > 0 && (
              <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
                {uploadedMedia.map((media) => (
                  <div key={media.id} className="relative group rounded-lg overflow-hidden border">
                    {media.type === 'IMAGE' ? (
                      <img
                        src={media.thumbnailUrl || media.url}
                        alt={media.fileName}
                        className="w-full h-32 object-cover"
                      />
                    ) : (
                      <div className="w-full h-32 bg-gray-100 flex items-center justify-center">
                        <Video className="w-8 h-8 text-gray-400" />
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={() => removeMedia(media.id)}
                      className="absolute top-1 right-1 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="w-4 h-4" />
                    </button>
                    <div className="p-2 bg-white">
                      <p className="text-xs truncate">{media.fileName}</p>
                      <p className="text-xs text-muted-foreground">
                        {(media.fileSize / 1024 / 1024).toFixed(1)}MB
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {isUploading && (
              <div className="mt-4 text-center text-sm text-muted-foreground">
                Uploading...
              </div>
            )}
          </CardContent>
        </Card>

        {/* Email Content */}
        <Card>
          <CardHeader>
            <CardTitle>📧 Email Newsletter</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Campaign Name *</Label>
              <Input
                id="name"
                name="name"
                placeholder="Week 1: AI Video Mini-Episode"
                required
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="subject">Email Subject *</Label>
              <Input
                id="subject"
                name="subject"
                placeholder="🎬 New Episode: The Future of AI Content"
                required
                disabled={isLoading}
                onChange={(e) => handleSubjectChange(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="htmlContent">Email Content *</Label>
              <textarea
                id="htmlContent"
                name="htmlContent"
                rows={6}
                placeholder="<h1>Check out this week's AI video!</h1>
<p>This week I explore...</p>
<a href='https://yoursite.com/video'>Watch Now</a>

{{unsubscribe_link}}"
                required
                disabled={isLoading}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 font-mono"
              />
            </div>
          </CardContent>
        </Card>

        {/* Social Media Distribution */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>📱 Social Media Distribution</CardTitle>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableSocial}
                  onChange={(e) => setEnableSocial(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-sm font-normal">Enable</span>
              </label>
            </div>
          </CardHeader>
          {enableSocial && (
            <CardContent className="space-y-4">
              {/* Platform Selection */}
              <div>
                <Label>Select Platforms</Label>
                <div className="flex gap-4 mt-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedPlatforms.instagram}
                      onChange={(e) =>
                        setSelectedPlatforms((prev) => ({
                          ...prev,
                          instagram: e.target.checked,
                        }))
                      }
                      className="w-4 h-4"
                    />
                    <Instagram className="w-5 h-5" />
                    <span className="text-sm">Instagram</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedPlatforms.facebook}
                      onChange={(e) =>
                        setSelectedPlatforms((prev) => ({
                          ...prev,
                          facebook: e.target.checked,
                        }))
                      }
                      className="w-4 h-4"
                    />
                    <Facebook className="w-5 h-5" />
                    <span className="text-sm">Facebook</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedPlatforms.tiktok}
                      onChange={(e) =>
                        setSelectedPlatforms((prev) => ({
                          ...prev,
                          tiktok: e.target.checked,
                        }))
                      }
                      className="w-4 h-4"
                    />
                    <Video className="w-5 h-5" />
                    <span className="text-sm">TikTok</span>
                  </label>
                </div>
              </div>

              {/* Social Caption */}
              <div className="space-y-2">
                <Label htmlFor="socialCaption">Social Media Caption</Label>
                <textarea
                  id="socialCaption"
                  value={socialCaption}
                  onChange={(e) => setSocialCaption(e.target.value)}
                  rows={3}
                  placeholder="Your caption for Instagram, Facebook, and TikTok..."
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  disabled={isLoading}
                />
                <p className="text-xs text-muted-foreground">
                  Max 2,200 characters (Instagram/TikTok limit)
                </p>
              </div>

              {/* Hashtags */}
              <div className="space-y-2">
                <Label htmlFor="hashtags">Hashtags</Label>
                <Input
                  id="hashtags"
                  value={hashtags}
                  onChange={(e) => setHashtags(e.target.value)}
                  placeholder="#AI #Content #Video #Ebook #Marketing"
                  disabled={isLoading}
                />
                <p className="text-xs text-muted-foreground">
                  Separate with spaces. Max 30 hashtags.
                </p>
              </div>

              {/* Platform Tips */}
              <div className="rounded-md bg-blue-50 p-3 text-sm text-blue-800">
                <p className="font-medium">📌 Tips:</p>
                <ul className="mt-1 space-y-1 text-xs list-disc list-inside">
                  <li>Instagram: Links won't be clickable (use "Link in bio")</li>
                  <li>Facebook: Links will be clickable and preview</li>
                  <li>TikTok: Videos will be optimized to 9:16 vertical</li>
                </ul>
              </div>
            </CardContent>
          )}
        </Card>

        {/* UTM Tracking (Collapsed) */}
        <details className="border rounded-lg">
          <summary className="p-4 cursor-pointer font-medium">
            🔗 UTM Tracking (Optional)
          </summary>
          <div className="p-4 pt-0 grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="utmSource">UTM Source</Label>
              <Input
                id="utmSource"
                name="utmSource"
                placeholder="newsletter"
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="utmMedium">UTM Medium</Label>
              <Input
                id="utmMedium"
                name="utmMedium"
                placeholder="email"
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="utmCampaign">UTM Campaign</Label>
              <Input
                id="utmCampaign"
                name="utmCampaign"
                placeholder="week-1-video"
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="utmContent">UTM Content</Label>
              <Input
                id="utmContent"
                name="utmContent"
                placeholder="ai-video"
                disabled={isLoading}
              />
            </div>
          </div>
        </details>

        {error && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">{error}</div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.back()}
            disabled={isLoading}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading || uploadedMedia.length === 0} className="flex-1">
            {isLoading ? 'Creating...' : '🚀 Create & Distribute'}
          </Button>
        </div>

        {uploadedMedia.length === 0 && (
          <p className="text-center text-sm text-muted-foreground">
            Upload at least one video or image to continue
          </p>
        )}
      </form>
    </div>
  );
}
