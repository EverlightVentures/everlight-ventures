/**
 * Social Media Publishing Utility
 * Handles posting to Instagram, Facebook, and TikTok with retry logic
 */

import {
  publishToInstagram,
  publishToFacebook,
  FacebookAPIError,
  isRetryableError,
  getRetryDelay,
} from './facebook-client';
import { decryptToken } from './encryption';
import { logActivity } from '@/lib/activity-logger';
import prisma from '@/lib/prisma';
import type { SocialMediaPlatform, Campaign, SocialMediaAccount } from '@prisma/client';

/**
 * Publishing options for social media
 */
export interface PublishOptions {
  caption: string;
  hashtags?: string[];
  imageUrl?: string;
  videoUrl?: string;
  link?: string;
}

/**
 * Publishing result
 */
export interface PublishResult {
  success: boolean;
  postId?: string;
  platformPostId?: string;
  error?: string;
  errorCode?: number;
  retried?: number;
}

/**
 * Publish with retry logic
 */
async function publishWithRetry<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  onRetry?: (attempt: number, error: any) => void
): Promise<T> {
  let lastError: any;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      if (attempt === maxRetries) {
        throw error;
      }

      // Check if error is retryable
      if (error instanceof FacebookAPIError && isRetryableError(error)) {
        const delay = getRetryDelay(error, attempt);
        console.log(
          `[Publisher] Retrying after ${delay}ms (attempt ${attempt + 1}/${maxRetries})`
        );

        if (onRetry) {
          onRetry(attempt + 1, error);
        }

        await new Promise(resolve => setTimeout(resolve, delay));
      } else {
        // Non-retryable error, throw immediately
        throw error;
      }
    }
  }

  throw lastError;
}

/**
 * Publish to Instagram
 */
async function publishInstagramPost(
  account: SocialMediaAccount,
  options: PublishOptions
): Promise<PublishResult> {
  try {
    if (!options.imageUrl) {
      return {
        success: false,
        error: 'Image URL is required for Instagram posts',
      };
    }

    // Decrypt access token
    const accessToken = decryptToken(account.accessToken);

    // Build caption with hashtags
    let caption = options.caption;
    if (options.hashtags && options.hashtags.length > 0) {
      caption += '\n\n' + options.hashtags.join(' ');
    }

    // Publish with retry
    const result = await publishWithRetry(
      () =>
        publishToInstagram(account.platformUserId, accessToken, {
          imageUrl: options.imageUrl!,
          caption,
        }),
      3,
      (attempt, error) => {
        console.log(
          `[Instagram] Retry attempt ${attempt} for account ${account.platformUsername}`,
          error.message
        );
      }
    );

    return {
      success: true,
      platformPostId: result.postId,
    };
  } catch (error) {
    console.error('[Instagram Publishing] Error:', error);

    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      errorCode: error instanceof FacebookAPIError ? error.code : undefined,
    };
  }
}

/**
 * Publish to Facebook
 */
async function publishFacebookPost(
  account: SocialMediaAccount,
  options: PublishOptions
): Promise<PublishResult> {
  try {
    // Decrypt access token
    const accessToken = decryptToken(account.accessToken);

    // Build message with hashtags
    let message = options.caption;
    if (options.hashtags && options.hashtags.length > 0) {
      message += '\n\n' + options.hashtags.join(' ');
    }

    // Publish with retry
    const result = await publishWithRetry(
      () =>
        publishToFacebook(account.platformUserId, accessToken, {
          message,
          link: options.link,
          photoUrl: options.imageUrl,
        }),
      3,
      (attempt, error) => {
        console.log(
          `[Facebook] Retry attempt ${attempt} for page ${account.platformUsername}`,
          error.message
        );
      }
    );

    return {
      success: true,
      platformPostId: result.postId,
    };
  } catch (error) {
    console.error('[Facebook Publishing] Error:', error);

    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      errorCode: error instanceof FacebookAPIError ? error.code : undefined,
    };
  }
}

/**
 * Publish to TikTok (placeholder for Phase 6)
 */
async function publishTikTokPost(
  account: SocialMediaAccount,
  options: PublishOptions
): Promise<PublishResult> {
  // TikTok API integration to be implemented in Phase 6
  return {
    success: false,
    error: 'TikTok publishing not yet implemented',
  };
}

/**
 * Publish to a specific platform
 */
async function publishToPlatform(
  account: SocialMediaAccount,
  platform: SocialMediaPlatform,
  options: PublishOptions
): Promise<PublishResult> {
  switch (platform) {
    case 'INSTAGRAM':
      return publishInstagramPost(account, options);
    case 'FACEBOOK':
      return publishFacebookPost(account, options);
    case 'TIKTOK':
      return publishTikTokPost(account, options);
    default:
      return {
        success: false,
        error: `Unknown platform: ${platform}`,
      };
  }
}

/**
 * Publish campaign to all connected social media accounts
 */
export async function publishCampaignToSocialMedia(
  campaign: Campaign & {
    project: { id: string; slug: string };
  }
): Promise<void> {
  try {
    // Get all connected social media accounts for this project
    const accounts = await prisma.socialMediaAccount.findMany({
      where: {
        projectId: campaign.project.id,
        status: 'CONNECTED',
      },
    });

    if (accounts.length === 0) {
      console.log('[Publisher] No connected social media accounts found');
      return;
    }

    // Prepare publishing options
    const caption = campaign.socialCaption || campaign.subject;
    const hashtags = campaign.socialHashtags;

    // Get first image from campaign assets (if any)
    const assets = await prisma.socialMediaAsset.findMany({
      where: {
        projectId: campaign.project.id,
      },
      orderBy: { createdAt: 'desc' },
      take: 1,
    });

    const imageUrl = assets[0]?.processedUrl || assets[0]?.url;

    if (!imageUrl) {
      console.warn('[Publisher] No image found for campaign, skipping social media posts');
      return;
    }

    const options: PublishOptions = {
      caption,
      hashtags,
      imageUrl: `${process.env.NEXTAUTH_URL}${imageUrl}`,
    };

    // Publish to each platform
    const publishPromises = accounts.map(async account => {
      try {
        // Create draft social media post record
        const post = await prisma.socialMediaPost.create({
          data: {
            platform: account.platform,
            caption,
            hashtags,
            status: 'PUBLISHING',
            projectId: campaign.project.id,
            accountId: account.id,
            campaignId: campaign.id,
          },
        });

        // Associate asset with post
        if (assets[0]) {
          await prisma.socialMediaAsset.update({
            where: { id: assets[0].id },
            data: { postId: post.id },
          });
        }

        // Publish
        const result = await publishToPlatform(account, account.platform, options);

        if (result.success && result.platformPostId) {
          // Update post as published
          await prisma.socialMediaPost.update({
            where: { id: post.id },
            data: {
              status: 'PUBLISHED',
              platformPostId: result.platformPostId,
              publishedAt: new Date(),
            },
          });

          // Log success
          await logActivity({
            type: 'SOCIAL_POST_PUBLISHED',
            projectId: campaign.project.id,
            metadata: {
              platform: account.platform,
              accountName: account.platformUsername,
              campaignName: campaign.name,
              postId: post.id,
            },
          });

          console.log(
            `[Publisher] Successfully published to ${account.platform} (${account.platformUsername})`
          );
        } else {
          // Update post as failed
          await prisma.socialMediaPost.update({
            where: { id: post.id },
            data: {
              status: 'FAILED',
              errorMessage: result.error,
            },
          });

          // Log failure
          await logActivity({
            type: 'SOCIAL_POST_FAILED',
            projectId: campaign.project.id,
            metadata: {
              platform: account.platform,
              accountName: account.platformUsername,
              campaignName: campaign.name,
              error: result.error,
            },
          });

          console.error(
            `[Publisher] Failed to publish to ${account.platform} (${account.platformUsername}):`,
            result.error
          );
        }
      } catch (error) {
        console.error(
          `[Publisher] Error publishing to ${account.platform} (${account.platformUsername}):`,
          error
        );

        // Log failure
        await logActivity({
          type: 'SOCIAL_POST_FAILED',
          projectId: campaign.project.id,
          metadata: {
            platform: account.platform,
            accountName: account.platformUsername,
            campaignName: campaign.name,
            error: error instanceof Error ? error.message : 'Unknown error',
          },
        });
      }
    });

    // Wait for all publishing attempts to complete (don't throw errors)
    await Promise.allSettled(publishPromises);
  } catch (error) {
    console.error('[Publisher] Error in publishCampaignToSocialMedia:', error);
    // Don't throw - social media failures shouldn't block email sending
  }
}

/**
 * Publish a single post to social media (for manual posting)
 */
export async function publishSocialPost(
  postId: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const post = await prisma.socialMediaPost.findUnique({
      where: { id: postId },
      include: {
        account: true,
        assets: true,
        project: true,
      },
    });

    if (!post) {
      return { success: false, error: 'Post not found' };
    }

    if (post.status === 'PUBLISHED') {
      return { success: false, error: 'Post already published' };
    }

    // Get image URL
    const imageUrl = post.assets[0]?.processedUrl || post.assets[0]?.url;

    if (!imageUrl) {
      return { success: false, error: 'No image found for post' };
    }

    const options: PublishOptions = {
      caption: post.caption || '',
      hashtags: post.hashtags,
      imageUrl: `${process.env.NEXTAUTH_URL}${imageUrl}`,
    };

    // Update status to publishing
    await prisma.socialMediaPost.update({
      where: { id: postId },
      data: { status: 'PUBLISHING' },
    });

    // Publish
    const result = await publishToPlatform(post.account, post.platform, options);

    if (result.success && result.platformPostId) {
      await prisma.socialMediaPost.update({
        where: { id: postId },
        data: {
          status: 'PUBLISHED',
          platformPostId: result.platformPostId,
          publishedAt: new Date(),
        },
      });

      await logActivity({
        type: 'SOCIAL_POST_PUBLISHED',
        projectId: post.project.id,
        metadata: {
          platform: post.platform,
          accountName: post.account.platformUsername,
          postId: post.id,
        },
      });

      return { success: true };
    } else {
      await prisma.socialMediaPost.update({
        where: { id: postId },
        data: {
          status: 'FAILED',
          errorMessage: result.error,
        },
      });

      return { success: false, error: result.error };
    }
  } catch (error) {
    console.error('[Publisher] Error in publishSocialPost:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}
