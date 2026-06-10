/**
 * Media processing utilities for social media assets
 * Handles image optimization and resizing for different platforms
 */

import sharp from 'sharp';
import { SocialMediaPlatform } from '@prisma/client';

/**
 * Platform-specific image requirements
 */
export const PLATFORM_IMAGE_SPECS = {
  INSTAGRAM: {
    maxSize: 8 * 1024 * 1024, // 8MB
    minWidth: 320,
    maxWidth: 1440,
    aspectRatios: {
      square: { width: 1080, height: 1080 },
      landscape: { width: 1080, height: 566 },
      portrait: { width: 1080, height: 1350 },
      story: { width: 1080, height: 1920 },
    },
    formats: ['image/jpeg', 'image/png'],
  },
  FACEBOOK: {
    maxSize: 4 * 1024 * 1024, // 4MB
    minWidth: 400,
    maxWidth: 2048,
    aspectRatios: {
      square: { width: 1200, height: 1200 },
      landscape: { width: 1200, height: 630 },
      portrait: { width: 1200, height: 1500 },
    },
    formats: ['image/jpeg', 'image/png'],
  },
  TIKTOK: {
    maxSize: 10 * 1024 * 1024, // 10MB
    minWidth: 480,
    maxWidth: 1440,
    aspectRatios: {
      vertical: { width: 1080, height: 1920 },
      square: { width: 1080, height: 1080 },
    },
    formats: ['image/jpeg', 'image/png'],
  },
} as const;

/**
 * Platform-specific video requirements
 */
export const PLATFORM_VIDEO_SPECS = {
  INSTAGRAM: {
    maxSize: 100 * 1024 * 1024, // 100MB for feed, 4GB for IGTV
    minDuration: 3, // seconds
    maxDuration: 60, // seconds (15 for stories, 60 for reels/feed)
    aspectRatios: {
      square: '1:1',
      landscape: '16:9',
      portrait: '4:5',
      vertical: '9:16', // Stories/Reels
    },
    formats: ['video/mp4', 'video/quicktime'],
    codecs: 'H.264',
  },
  FACEBOOK: {
    maxSize: 4 * 1024 * 1024 * 1024, // 4GB
    minDuration: 1,
    maxDuration: 240 * 60, // 240 minutes
    aspectRatios: {
      square: '1:1',
      landscape: '16:9',
      portrait: '9:16',
    },
    formats: ['video/mp4', 'video/quicktime'],
    codecs: 'H.264',
  },
  TIKTOK: {
    maxSize: 287 * 1024 * 1024, // 287MB
    minDuration: 3,
    maxDuration: 10 * 60, // 10 minutes
    aspectRatios: {
      vertical: '9:16',
    },
    formats: ['video/mp4', 'video/quicktime', 'video/webm'],
    codecs: 'H.264',
  },
} as const;

/**
 * Validate image file
 */
export async function validateImage(
  buffer: Buffer,
  platform: SocialMediaPlatform
): Promise<{ valid: boolean; error?: string; metadata?: sharp.Metadata }> {
  try {
    const image = sharp(buffer);
    const metadata = await image.metadata();

    const specs = PLATFORM_IMAGE_SPECS[platform];

    // Check format
    if (!metadata.format) {
      return { valid: false, error: 'Unable to determine image format' };
    }

    const mimeType = `image/${metadata.format}`;
    if (!specs.formats.includes(mimeType as any)) {
      return {
        valid: false,
        error: `Invalid format for ${platform}. Supported: ${specs.formats.join(', ')}`,
      };
    }

    // Check dimensions
    if (metadata.width && metadata.width < specs.minWidth) {
      return {
        valid: false,
        error: `Image width must be at least ${specs.minWidth}px`,
      };
    }

    if (metadata.width && metadata.width > specs.maxWidth) {
      return {
        valid: false,
        error: `Image width must not exceed ${specs.maxWidth}px`,
      };
    }

    // Check file size
    if (buffer.length > specs.maxSize) {
      return {
        valid: false,
        error: `Image size must not exceed ${specs.maxSize / (1024 * 1024)}MB`,
      };
    }

    return { valid: true, metadata };
  } catch (error) {
    return {
      valid: false,
      error: `Failed to validate image: ${error instanceof Error ? error.message : 'Unknown error'}`,
    };
  }
}

/**
 * Optimize image for platform
 */
export async function optimizeImage(
  buffer: Buffer,
  platform: SocialMediaPlatform,
  targetAspectRatio?: 'square' | 'landscape' | 'portrait' | 'story' | 'vertical'
): Promise<{ buffer: Buffer; metadata: sharp.Metadata }> {
  const specs = PLATFORM_IMAGE_SPECS[platform];
  let image = sharp(buffer);
  const metadata = await image.metadata();

  // Determine target dimensions
  let targetWidth: number;
  let targetHeight: number;

  if (targetAspectRatio && targetAspectRatio in specs.aspectRatios) {
    const ratio = specs.aspectRatios[targetAspectRatio as keyof typeof specs.aspectRatios];
    targetWidth = ratio.width;
    targetHeight = ratio.height;
  } else {
    // Keep original aspect ratio but constrain to max width
    targetWidth = Math.min(metadata.width || specs.maxWidth, specs.maxWidth);
    targetHeight = Math.round(
      targetWidth * ((metadata.height || 1) / (metadata.width || 1))
    );
  }

  // Resize and optimize
  image = image
    .resize(targetWidth, targetHeight, {
      fit: targetAspectRatio ? 'cover' : 'inside',
      position: 'center',
    })
    .jpeg({ quality: 85, progressive: true })
    .withMetadata();

  const optimizedBuffer = await image.toBuffer();
  const optimizedMetadata = await sharp(optimizedBuffer).metadata();

  // If still too large, reduce quality
  if (optimizedBuffer.length > specs.maxSize) {
    const qualityReduction = Math.floor((specs.maxSize / optimizedBuffer.length) * 85);
    const finalBuffer = await sharp(buffer)
      .resize(targetWidth, targetHeight, {
        fit: targetAspectRatio ? 'cover' : 'inside',
        position: 'center',
      })
      .jpeg({ quality: Math.max(qualityReduction, 60), progressive: true })
      .toBuffer();

    const finalMetadata = await sharp(finalBuffer).metadata();
    return { buffer: finalBuffer, metadata: finalMetadata };
  }

  return { buffer: optimizedBuffer, metadata: optimizedMetadata };
}

/**
 * Generate thumbnail for image or video
 */
export async function generateThumbnail(
  buffer: Buffer,
  width: number = 300,
  height: number = 300
): Promise<Buffer> {
  return sharp(buffer)
    .resize(width, height, {
      fit: 'cover',
      position: 'center',
    })
    .jpeg({ quality: 80 })
    .toBuffer();
}

/**
 * Extract metadata from image
 */
export async function extractImageMetadata(buffer: Buffer): Promise<{
  width?: number;
  height?: number;
  format?: string;
  size: number;
}> {
  const metadata = await sharp(buffer).metadata();

  return {
    width: metadata.width,
    height: metadata.height,
    format: metadata.format,
    size: buffer.length,
  };
}

/**
 * Validate video file (basic validation without ffmpeg processing)
 */
export function validateVideo(
  fileSize: number,
  mimeType: string,
  platform: SocialMediaPlatform
): { valid: boolean; error?: string } {
  const specs = PLATFORM_VIDEO_SPECS[platform];

  // Check format
  if (!specs.formats.includes(mimeType as any)) {
    return {
      valid: false,
      error: `Invalid video format for ${platform}. Supported: ${specs.formats.join(', ')}`,
    };
  }

  // Check file size
  if (fileSize > specs.maxSize) {
    return {
      valid: false,
      error: `Video size must not exceed ${specs.maxSize / (1024 * 1024)}MB`,
    };
  }

  return { valid: true };
}

/**
 * Get recommended aspect ratio for platform and content type
 */
export function getRecommendedAspectRatio(
  platform: SocialMediaPlatform,
  contentType: 'feed' | 'story' | 'reel'
): string {
  switch (platform) {
    case 'INSTAGRAM':
      if (contentType === 'story' || contentType === 'reel') return '9:16';
      return '4:5'; // Portrait for feed
    case 'FACEBOOK':
      return '1:1'; // Square performs best
    case 'TIKTOK':
      return '9:16'; // Vertical only
    default:
      return '1:1';
  }
}

/**
 * Calculate aspect ratio from dimensions
 */
export function calculateAspectRatio(width: number, height: number): string {
  const gcd = (a: number, b: number): number => (b === 0 ? a : gcd(b, a % b));
  const divisor = gcd(width, height);
  return `${width / divisor}:${height / divisor}`;
}

/**
 * Check if aspect ratio matches target (with tolerance)
 */
export function isAspectRatioMatch(
  actualRatio: string,
  targetRatio: string,
  tolerance: number = 0.05
): boolean {
  const parseRatio = (ratio: string): number => {
    const [w, h] = ratio.split(':').map(Number);
    return w / h;
  };

  const actual = parseRatio(actualRatio);
  const target = parseRatio(targetRatio);

  return Math.abs(actual - target) / target <= tolerance;
}
