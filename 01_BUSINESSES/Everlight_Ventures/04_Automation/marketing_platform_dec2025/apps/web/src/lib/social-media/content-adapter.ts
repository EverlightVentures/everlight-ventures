/**
 * Content adaptation utilities for converting email HTML to social media captions
 * Handles platform-specific character limits, link handling, and hashtag optimization
 */

import * as cheerio from 'cheerio';
import { SocialMediaPlatform } from '@prisma/client';

/**
 * Platform-specific content requirements
 */
export const PLATFORM_CONTENT_SPECS = {
  INSTAGRAM: {
    maxCaptionLength: 2200,
    maxHashtags: 30,
    supportsClickableLinks: false, // Links not clickable in captions
    linkInBioStrategy: true,
  },
  FACEBOOK: {
    maxCaptionLength: 63206,
    maxHashtags: 30, // No hard limit, but 30 is best practice
    supportsClickableLinks: true,
    linkInBioStrategy: false,
  },
  TIKTOK: {
    maxCaptionLength: 2200,
    maxHashtags: 30,
    supportsClickableLinks: false, // Limited link support
    linkInBioStrategy: true,
  },
} as const;

/**
 * Extract plain text from HTML
 */
export function htmlToPlainText(html: string): string {
  const $ = cheerio.load(html);

  // Remove script and style elements
  $('script, style').remove();

  // Get text content
  let text = $.text();

  // Clean up whitespace
  text = text.replace(/\s+/g, ' ').trim();

  return text;
}

/**
 * Extract links from HTML
 */
export function extractLinksFromHTML(html: string): Array<{
  url: string;
  text: string;
}> {
  const $ = cheerio.load(html);
  const links: Array<{ url: string; text: string }> = [];

  $('a[href]').each((_, element) => {
    const url = $(element).attr('href');
    const text = $(element).text().trim();

    if (url && !url.includes('unsubscribe')) {
      links.push({ url, text });
    }
  });

  return links;
}

/**
 * Extract images from HTML
 */
export function extractImagesFromHTML(html: string): Array<{
  src: string;
  alt?: string;
}> {
  const $ = cheerio.load(html);
  const images: Array<{ src: string; alt?: string }> = [];

  $('img[src]').each((_, element) => {
    const src = $(element).attr('src');
    const alt = $(element).attr('alt');

    // Skip tracking pixels (1x1 images)
    const width = $(element).attr('width');
    const height = $(element).attr('height');

    if (src && !(width === '1' && height === '1')) {
      images.push({ src, alt });
    }
  });

  return images;
}

/**
 * Extract or generate hashtags from content
 */
export function extractHashtags(text: string): string[] {
  const hashtagRegex = /#[\w\u0590-\u05ff]+/gi;
  const matches = text.match(hashtagRegex);
  return matches ? [...new Set(matches.map(tag => tag.toLowerCase()))] : [];
}

/**
 * Generate hashtags from keywords
 */
export function generateHashtags(keywords: string[]): string[] {
  return keywords
    .map(keyword => {
      // Remove special characters and spaces
      const cleaned = keyword.replace(/[^\w\s]/g, '').replace(/\s+/g, '');
      return cleaned ? `#${cleaned}` : null;
    })
    .filter(Boolean) as string[];
}

/**
 * Truncate text to fit platform limits
 */
export function truncateText(
  text: string,
  maxLength: number,
  suffix: string = '...'
): string {
  if (text.length <= maxLength) {
    return text;
  }

  const truncated = text.slice(0, maxLength - suffix.length);
  // Try to break at last complete word
  const lastSpace = truncated.lastIndexOf(' ');

  if (lastSpace > 0) {
    return truncated.slice(0, lastSpace) + suffix;
  }

  return truncated + suffix;
}

/**
 * Convert email HTML to social media caption
 */
export function htmlToSocialCaption(
  html: string,
  platform: SocialMediaPlatform,
  options?: {
    includeLinks?: boolean;
    includeCTA?: boolean;
    customHashtags?: string[];
  }
): string {
  const specs = PLATFORM_CONTENT_SPECS[platform];
  const plainText = htmlToPlainText(html);

  let caption = plainText;

  // Add links based on platform capabilities
  if (options?.includeLinks) {
    const links = extractLinksFromHTML(html);

    if (specs.supportsClickableLinks && links.length > 0) {
      // Facebook: Add clickable links
      caption += '\n\n';
      links.slice(0, 3).forEach(link => {
        caption += `\n🔗 ${link.text}: ${link.url}`;
      });
    } else if (specs.linkInBioStrategy && links.length > 0) {
      // Instagram/TikTok: Use "link in bio" strategy
      caption += '\n\n🔗 Link in bio for more!';
    }
  }

  // Add custom hashtags
  if (options?.customHashtags && options.customHashtags.length > 0) {
    const hashtags = options.customHashtags.slice(0, specs.maxHashtags);
    caption += '\n\n' + hashtags.join(' ');
  }

  // Truncate to platform limit
  caption = truncateText(caption, specs.maxCaptionLength);

  return caption;
}

/**
 * Adapt content specifically for Instagram
 */
export function adaptForInstagram(
  html: string,
  options?: {
    hashtags?: string[];
    linkInBio?: string;
  }
): {
  caption: string;
  links: Array<{ url: string; text: string }>;
} {
  const plainText = htmlToPlainText(html);
  const links = extractLinksFromHTML(html);

  let caption = plainText;

  // Instagram-specific formatting
  if (options?.linkInBio && links.length > 0) {
    caption += '\n\n🔗 ' + options.linkInBio;
  }

  // Add hashtags at the end
  if (options?.hashtags && options.hashtags.length > 0) {
    const hashtagLine = '\n\n' + options.hashtags.slice(0, 30).join(' ');
    caption += hashtagLine;
  }

  // Truncate to 2200 characters
  caption = truncateText(caption, 2200);

  return { caption, links };
}

/**
 * Adapt content specifically for Facebook
 */
export function adaptForFacebook(
  html: string,
  options?: {
    hashtags?: string[];
  }
): {
  caption: string;
  links: Array<{ url: string; text: string }>;
} {
  const plainText = htmlToPlainText(html);
  const links = extractLinksFromHTML(html);

  let caption = plainText;

  // Facebook supports clickable links
  if (links.length > 0) {
    caption += '\n\n';
    links.slice(0, 5).forEach(link => {
      caption += `\n🔗 ${link.text}: ${link.url}`;
    });
  }

  // Add hashtags
  if (options?.hashtags && options.hashtags.length > 0) {
    caption += '\n\n' + options.hashtags.slice(0, 30).join(' ');
  }

  // Facebook has high limit, but still truncate for safety
  caption = truncateText(caption, 10000);

  return { caption, links };
}

/**
 * Adapt content specifically for TikTok
 */
export function adaptForTikTok(
  html: string,
  options?: {
    hashtags?: string[];
  }
): {
  caption: string;
  links: Array<{ url: string; text: string }>;
} {
  const plainText = htmlToPlainText(html);
  const links = extractLinksFromHTML(html);

  let caption = plainText;

  // TikTok has limited link support, focus on hashtags
  if (options?.hashtags && options.hashtags.length > 0) {
    caption += '\n\n' + options.hashtags.slice(0, 30).join(' ');
  }

  // Truncate to 2200 characters
  caption = truncateText(caption, 2200);

  return { caption, links };
}

/**
 * Optimize hashtags for engagement
 */
export function optimizeHashtags(
  hashtags: string[],
  platform: SocialMediaPlatform
): string[] {
  const specs = PLATFORM_CONTENT_SPECS[platform];

  // Remove duplicates and empty tags
  const uniqueTags = [...new Set(hashtags)]
    .filter(tag => tag && tag.length > 1)
    .map(tag => tag.toLowerCase());

  // Limit to platform maximum
  return uniqueTags.slice(0, specs.maxHashtags);
}

/**
 * Create call-to-action text
 */
export function generateCTA(
  type: 'link' | 'shop' | 'learn' | 'subscribe',
  platform: SocialMediaPlatform
): string {
  const ctas = {
    link: {
      INSTAGRAM: '🔗 Link in bio',
      FACEBOOK: '👉 Click the link to learn more',
      TIKTOK: '🔗 Check out the link',
    },
    shop: {
      INSTAGRAM: '🛍️ Shop now - Link in bio',
      FACEBOOK: '🛍️ Shop now',
      TIKTOK: '🛍️ Link in bio to shop',
    },
    learn: {
      INSTAGRAM: '📚 Learn more - Link in bio',
      FACEBOOK: '📚 Click to learn more',
      TIKTOK: '📚 Link in bio',
    },
    subscribe: {
      INSTAGRAM: '✉️ Subscribe via link in bio',
      FACEBOOK: '✉️ Subscribe now',
      TIKTOK: '✉️ Link in bio to subscribe',
    },
  };

  return ctas[type][platform];
}

/**
 * Auto-generate social caption from email campaign
 */
export function autoGenerateSocialCaption(
  emailHTML: string,
  platform: SocialMediaPlatform,
  options?: {
    maxLength?: number;
    includeEmojis?: boolean;
    addCTA?: boolean;
    hashtags?: string[];
  }
): string {
  const plainText = htmlToPlainText(emailHTML);
  const links = extractLinksFromHTML(html);
  const specs = PLATFORM_CONTENT_SPECS[platform];

  // Extract first paragraph as main message
  const firstParagraph = plainText.split('\n')[0];
  let caption = firstParagraph;

  // Add CTA if requested
  if (options?.addCTA && links.length > 0) {
    caption += '\n\n' + generateCTA('link', platform);
  }

  // Add hashtags
  if (options?.hashtags && options.hashtags.length > 0) {
    const optimized = optimizeHashtags(options.hashtags, platform);
    caption += '\n\n' + optimized.join(' ');
  }

  // Truncate
  const maxLen = options?.maxLength || specs.maxCaptionLength;
  caption = truncateText(caption, maxLen);

  return caption;
}
