/**
 * Facebook and Instagram Graph API client
 * Handles OAuth, posting, and engagement metrics
 */

const FACEBOOK_GRAPH_API_VERSION = 'v21.0';
const FACEBOOK_GRAPH_API_BASE = `https://graph.facebook.com/${FACEBOOK_GRAPH_API_VERSION}`;

/**
 * Facebook/Instagram API error
 */
export class FacebookAPIError extends Error {
  constructor(
    message: string,
    public code: number,
    public type: string,
    public fbTraceId?: string
  ) {
    super(message);
    this.name = 'FacebookAPIError';
  }
}

/**
 * OAuth configuration
 */
export interface FacebookOAuthConfig {
  appId: string;
  appSecret: string;
  redirectUri: string;
}

/**
 * Generate Facebook OAuth URL
 */
export function generateFacebookOAuthUrl(config: FacebookOAuthConfig, state: string): string {
  const scopes = [
    'pages_manage_posts',
    'pages_read_engagement',
    'instagram_basic',
    'instagram_content_publish',
  ];

  const params = new URLSearchParams({
    client_id: config.appId,
    redirect_uri: config.redirectUri,
    scope: scopes.join(','),
    state,
    response_type: 'code',
  });

  return `https://www.facebook.com/${FACEBOOK_GRAPH_API_VERSION}/dialog/oauth?${params.toString()}`;
}

/**
 * Exchange authorization code for access token
 */
export async function exchangeCodeForToken(
  code: string,
  config: FacebookOAuthConfig
): Promise<{
  accessToken: string;
  tokenType: string;
  expiresIn?: number;
}> {
  const params = new URLSearchParams({
    client_id: config.appId,
    client_secret: config.appSecret,
    redirect_uri: config.redirectUri,
    code,
  });

  const response = await fetch(
    `${FACEBOOK_GRAPH_API_BASE}/oauth/access_token?${params.toString()}`
  );

  const data = await response.json();

  if (!response.ok || data.error) {
    throw new FacebookAPIError(
      data.error?.message || 'Failed to exchange code for token',
      data.error?.code || response.status,
      data.error?.type || 'unknown',
      data.error?.fbtrace_id
    );
  }

  return {
    accessToken: data.access_token,
    tokenType: data.token_type,
    expiresIn: data.expires_in,
  };
}

/**
 * Exchange short-lived token for long-lived token
 */
export async function getLongLivedToken(
  shortLivedToken: string,
  config: FacebookOAuthConfig
): Promise<{
  accessToken: string;
  tokenType: string;
  expiresIn: number;
}> {
  const params = new URLSearchParams({
    grant_type: 'fb_exchange_token',
    client_id: config.appId,
    client_secret: config.appSecret,
    fb_exchange_token: shortLivedToken,
  });

  const response = await fetch(
    `${FACEBOOK_GRAPH_API_BASE}/oauth/access_token?${params.toString()}`
  );

  const data = await response.json();

  if (!response.ok || data.error) {
    throw new FacebookAPIError(
      data.error?.message || 'Failed to get long-lived token',
      data.error?.code || response.status,
      data.error?.type || 'unknown',
      data.error?.fbtrace_id
    );
  }

  return {
    accessToken: data.access_token,
    tokenType: data.token_type,
    expiresIn: data.expires_in,
  };
}

/**
 * Get user's Facebook Pages
 */
export async function getUserPages(accessToken: string): Promise<
  Array<{
    id: string;
    name: string;
    accessToken: string;
    category: string;
  }>
> {
  const response = await fetch(
    `${FACEBOOK_GRAPH_API_BASE}/me/accounts?access_token=${accessToken}`
  );

  const data = await response.json();

  if (!response.ok || data.error) {
    throw new FacebookAPIError(
      data.error?.message || 'Failed to get user pages',
      data.error?.code || response.status,
      data.error?.type || 'unknown',
      data.error?.fbtrace_id
    );
  }

  return data.data || [];
}

/**
 * Get Instagram Business Account connected to Facebook Page
 */
export async function getInstagramAccount(
  pageId: string,
  pageAccessToken: string
): Promise<{
  id: string;
  username?: string;
} | null> {
  const response = await fetch(
    `${FACEBOOK_GRAPH_API_BASE}/${pageId}?fields=instagram_business_account&access_token=${pageAccessToken}`
  );

  const data = await response.json();

  if (!response.ok || data.error) {
    throw new FacebookAPIError(
      data.error?.message || 'Failed to get Instagram account',
      data.error?.code || response.status,
      data.error?.type || 'unknown',
      data.error?.fbtrace_id
    );
  }

  if (!data.instagram_business_account) {
    return null;
  }

  return {
    id: data.instagram_business_account.id,
  };
}

/**
 * Get Instagram account profile info
 */
export async function getInstagramProfile(
  igAccountId: string,
  accessToken: string
): Promise<{
  id: string;
  username: string;
  name?: string;
  profilePictureUrl?: string;
}> {
  const response = await fetch(
    `${FACEBOOK_GRAPH_API_BASE}/${igAccountId}?fields=id,username,name,profile_picture_url&access_token=${accessToken}`
  );

  const data = await response.json();

  if (!response.ok || data.error) {
    throw new FacebookAPIError(
      data.error?.message || 'Failed to get Instagram profile',
      data.error?.code || response.status,
      data.error?.type || 'unknown',
      data.error?.fbtrace_id
    );
  }

  return {
    id: data.id,
    username: data.username,
    name: data.name,
    profilePictureUrl: data.profile_picture_url,
  };
}

/**
 * Publish to Instagram (two-step process)
 */
export async function publishToInstagram(
  igAccountId: string,
  accessToken: string,
  options: {
    imageUrl: string;
    caption?: string;
    locationId?: string;
  }
): Promise<{
  postId: string;
}> {
  // Step 1: Create media container
  const containerParams = new URLSearchParams({
    image_url: options.imageUrl,
    caption: options.caption || '',
    access_token: accessToken,
  });

  if (options.locationId) {
    containerParams.append('location_id', options.locationId);
  }

  const containerResponse = await fetch(
    `${FACEBOOK_GRAPH_API_BASE}/${igAccountId}/media`,
    {
      method: 'POST',
      body: containerParams,
    }
  );

  const containerData = await containerResponse.json();

  if (!containerResponse.ok || containerData.error) {
    throw new FacebookAPIError(
      containerData.error?.message || 'Failed to create Instagram media container',
      containerData.error?.code || containerResponse.status,
      containerData.error?.type || 'unknown',
      containerData.error?.fbtrace_id
    );
  }

  const containerId = containerData.id;

  // Step 2: Publish the container
  const publishParams = new URLSearchParams({
    creation_id: containerId,
    access_token: accessToken,
  });

  const publishResponse = await fetch(
    `${FACEBOOK_GRAPH_API_BASE}/${igAccountId}/media_publish`,
    {
      method: 'POST',
      body: publishParams,
    }
  );

  const publishData = await publishResponse.json();

  if (!publishResponse.ok || publishData.error) {
    throw new FacebookAPIError(
      publishData.error?.message || 'Failed to publish Instagram media',
      publishData.error?.code || publishResponse.status,
      publishData.error?.type || 'unknown',
      publishData.error?.fbtrace_id
    );
  }

  return {
    postId: publishData.id,
  };
}

/**
 * Publish to Facebook Page
 */
export async function publishToFacebook(
  pageId: string,
  pageAccessToken: string,
  options: {
    message?: string;
    link?: string;
    photoUrl?: string;
  }
): Promise<{
  postId: string;
}> {
  let endpoint = `${FACEBOOK_GRAPH_API_BASE}/${pageId}/feed`;
  const params = new URLSearchParams({
    access_token: pageAccessToken,
  });

  if (options.message) {
    params.append('message', options.message);
  }

  if (options.link) {
    params.append('link', options.link);
  }

  // If photo URL is provided, use photos endpoint instead
  if (options.photoUrl) {
    endpoint = `${FACEBOOK_GRAPH_API_BASE}/${pageId}/photos`;
    params.append('url', options.photoUrl);
  }

  const response = await fetch(endpoint, {
    method: 'POST',
    body: params,
  });

  const data = await response.json();

  if (!response.ok || data.error) {
    throw new FacebookAPIError(
      data.error?.message || 'Failed to publish to Facebook',
      data.error?.code || response.status,
      data.error?.type || 'unknown',
      data.error?.fbtrace_id
    );
  }

  return {
    postId: data.id || data.post_id,
  };
}

/**
 * Get Instagram post insights/metrics
 */
export async function getInstagramPostMetrics(
  postId: string,
  accessToken: string
): Promise<{
  likeCount: number;
  commentCount: number;
  reach: number;
  impressions: number;
  saved: number;
}> {
  const response = await fetch(
    `${FACEBOOK_GRAPH_API_BASE}/${postId}/insights?metric=engagement,impressions,reach,saved&access_token=${accessToken}`
  );

  const data = await response.json();

  if (!response.ok || data.error) {
    // If insights not available yet, return zeros
    if (data.error?.code === 10 || data.error?.code === 100) {
      return {
        likeCount: 0,
        commentCount: 0,
        reach: 0,
        impressions: 0,
        saved: 0,
      };
    }

    throw new FacebookAPIError(
      data.error?.message || 'Failed to get Instagram metrics',
      data.error?.code || response.status,
      data.error?.type || 'unknown',
      data.error?.fbtrace_id
    );
  }

  // Also get like and comment counts
  const postResponse = await fetch(
    `${FACEBOOK_GRAPH_API_BASE}/${postId}?fields=like_count,comments_count&access_token=${accessToken}`
  );

  const postData = await postResponse.json();

  const metrics = data.data.reduce((acc: any, item: any) => {
    acc[item.name] = item.values[0]?.value || 0;
    return acc;
  }, {});

  return {
    likeCount: postData.like_count || 0,
    commentCount: postData.comments_count || 0,
    reach: metrics.reach || 0,
    impressions: metrics.impressions || 0,
    saved: metrics.saved || 0,
  };
}

/**
 * Get Facebook post metrics
 */
export async function getFacebookPostMetrics(
  postId: string,
  accessToken: string
): Promise<{
  likeCount: number;
  commentCount: number;
  shareCount: number;
  reach: number;
  impressions: number;
}> {
  const response = await fetch(
    `${FACEBOOK_GRAPH_API_BASE}/${postId}?fields=likes.summary(true),comments.summary(true),shares&access_token=${accessToken}`
  );

  const data = await response.json();

  if (!response.ok || data.error) {
    throw new FacebookAPIError(
      data.error?.message || 'Failed to get Facebook metrics',
      data.error?.code || response.status,
      data.error?.type || 'unknown',
      data.error?.fbtrace_id
    );
  }

  // Get insights (reach, impressions)
  const insightsResponse = await fetch(
    `${FACEBOOK_GRAPH_API_BASE}/${postId}/insights?metric=post_impressions,post_impressions_unique&access_token=${accessToken}`
  );

  const insightsData = await insightsResponse.json();

  const insights = insightsData.data?.reduce((acc: any, item: any) => {
    acc[item.name] = item.values[0]?.value || 0;
    return acc;
  }, {}) || {};

  return {
    likeCount: data.likes?.summary?.total_count || 0,
    commentCount: data.comments?.summary?.total_count || 0,
    shareCount: data.shares?.count || 0,
    reach: insights.post_impressions_unique || 0,
    impressions: insights.post_impressions || 0,
  };
}

/**
 * Check if error is retryable
 */
export function isRetryableError(error: FacebookAPIError): boolean {
  // Rate limit errors
  if (error.code === 4 || error.code === 17 || error.code === 32 || error.code === 613) {
    return true;
  }

  // Temporary errors
  if (error.code >= 500 && error.code < 600) {
    return true;
  }

  return false;
}

/**
 * Get retry delay for rate limit errors
 */
export function getRetryDelay(error: FacebookAPIError, attempt: number): number {
  // Exponential backoff: 2^attempt * 1000ms
  const baseDelay = Math.pow(2, attempt) * 1000;

  // Add jitter
  const jitter = Math.random() * 1000;

  return baseDelay + jitter;
}
