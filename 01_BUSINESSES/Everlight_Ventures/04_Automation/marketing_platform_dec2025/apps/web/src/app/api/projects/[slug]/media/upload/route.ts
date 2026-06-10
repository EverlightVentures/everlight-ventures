/**
 * Media upload API endpoint for social media assets
 * Handles image and video uploads for social media posts
 */

import { NextRequest, NextResponse } from 'next/server';
import { writeFile, mkdir } from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';
import prisma from '@/lib/prisma';
import {
  validateImage,
  validateVideo,
  optimizeImage,
  generateThumbnail,
  extractImageMetadata,
} from '@/lib/social-media/media-processor';
import { SocialMediaPlatform, SocialMediaAssetType } from '@prisma/client';

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/quicktime', 'video/webm'];

// Upload directory for local development
const UPLOAD_DIR = path.join(process.cwd(), 'public', 'uploads', 'social-media');

/**
 * Ensure upload directory exists
 */
async function ensureUploadDir() {
  if (!existsSync(UPLOAD_DIR)) {
    await mkdir(UPLOAD_DIR, { recursive: true });
  }
}

/**
 * Generate unique filename
 */
function generateFilename(originalName: string): string {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 8);
  const ext = path.extname(originalName);
  const baseName = path.basename(originalName, ext).replace(/[^a-z0-9]/gi, '-').toLowerCase();
  return `${timestamp}-${random}-${baseName}${ext}`;
}

/**
 * Save file locally (development)
 */
async function saveFileLocally(buffer: Buffer, filename: string): Promise<string> {
  await ensureUploadDir();
  const filePath = path.join(UPLOAD_DIR, filename);
  await writeFile(filePath, buffer);

  // Return public URL
  return `/uploads/social-media/${filename}`;
}

/**
 * POST /api/projects/[slug]/media/upload
 * Upload media file for social media
 */
export async function POST(
  request: NextRequest,
  { params }: { params: { slug: string } }
) {
  try {
    const { slug } = params;

    // Get project
    const project = await prisma.project.findUnique({
      where: { slug },
    });

    if (!project) {
      return NextResponse.json(
        { error: 'Project not found' },
        { status: 404 }
      );
    }

    // Parse form data
    const formData = await request.formData();
    const file = formData.get('file') as File | null;
    const platformStr = formData.get('platform') as string | null;
    const assetTypeStr = formData.get('assetType') as string | null;

    if (!file) {
      return NextResponse.json(
        { error: 'No file provided' },
        { status: 400 }
      );
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json(
        { error: `File size must not exceed ${MAX_FILE_SIZE / (1024 * 1024)}MB` },
        { status: 400 }
      );
    }

    // Determine asset type and validate
    const mimeType = file.type;
    let assetType: SocialMediaAssetType;
    let isImage = false;
    let isVideo = false;

    if (ALLOWED_IMAGE_TYPES.includes(mimeType)) {
      assetType = assetTypeStr === 'STORY' ? 'STORY' : 'IMAGE';
      isImage = true;
    } else if (ALLOWED_VIDEO_TYPES.includes(mimeType)) {
      assetType = assetTypeStr === 'REEL' ? 'REEL' : 'VIDEO';
      isVideo = true;
    } else {
      return NextResponse.json(
        { error: 'Invalid file type. Supported: JPEG, PNG, WebP, MP4, QuickTime, WebM' },
        { status: 400 }
      );
    }

    // Convert file to buffer
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    // Validate based on platform if provided
    if (platformStr && ['INSTAGRAM', 'FACEBOOK', 'TIKTOK'].includes(platformStr)) {
      const platform = platformStr as SocialMediaPlatform;

      if (isImage) {
        const validation = await validateImage(buffer, platform);
        if (!validation.valid) {
          return NextResponse.json(
            { error: validation.error },
            { status: 400 }
          );
        }
      } else if (isVideo) {
        const validation = validateVideo(file.size, mimeType, platform);
        if (!validation.valid) {
          return NextResponse.json(
            { error: validation.error },
            { status: 400 }
          );
        }
      }
    }

    // Generate filename and save
    const filename = generateFilename(file.name);
    const url = await saveFileLocally(buffer, filename);

    // Process image if needed
    let processedUrl: string | undefined;
    let thumbnailUrl: string | undefined;
    let width: number | undefined;
    let height: number | undefined;

    if (isImage) {
      // Optimize image for web
      const optimized = await optimizeImage(
        buffer,
        platformStr as SocialMediaPlatform || 'INSTAGRAM'
      );

      const optimizedFilename = `optimized-${filename}`;
      processedUrl = await saveFileLocally(optimized.buffer, optimizedFilename);

      // Generate thumbnail
      const thumbnail = await generateThumbnail(buffer, 300, 300);
      const thumbnailFilename = `thumb-${filename}`;
      thumbnailUrl = await saveFileLocally(thumbnail, thumbnailFilename);

      // Extract metadata
      const metadata = await extractImageMetadata(buffer);
      width = metadata.width;
      height = metadata.height;
    }

    // Create database record
    const asset = await prisma.socialMediaAsset.create({
      data: {
        type: assetType,
        fileName: file.name,
        fileSize: file.size,
        mimeType,
        url,
        thumbnailUrl,
        width,
        height,
        isProcessed: !!processedUrl,
        processedUrl,
        projectId: project.id,
      },
    });

    return NextResponse.json({
      success: true,
      asset: {
        id: asset.id,
        type: asset.type,
        url: asset.url,
        thumbnailUrl: asset.thumbnailUrl,
        processedUrl: asset.processedUrl,
        fileName: asset.fileName,
        fileSize: asset.fileSize,
        width: asset.width,
        height: asset.height,
      },
    });
  } catch (error) {
    console.error('[Media Upload] Error:', error);
    return NextResponse.json(
      {
        error: 'Failed to upload media',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

/**
 * GET /api/projects/[slug]/media/upload
 * Get uploaded media assets for a project
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { slug: string } }
) {
  try {
    const { slug } = params;

    // Get project
    const project = await prisma.project.findUnique({
      where: { slug },
    });

    if (!project) {
      return NextResponse.json(
        { error: 'Project not found' },
        { status: 404 }
      );
    }

    // Get all assets for project
    const assets = await prisma.socialMediaAsset.findMany({
      where: { projectId: project.id },
      orderBy: { createdAt: 'desc' },
      select: {
        id: true,
        type: true,
        fileName: true,
        fileSize: true,
        mimeType: true,
        url: true,
        thumbnailUrl: true,
        processedUrl: true,
        width: true,
        height: true,
        duration: true,
        isProcessed: true,
        createdAt: true,
      },
    });

    return NextResponse.json({
      success: true,
      assets,
    });
  } catch (error) {
    console.error('[Media List] Error:', error);
    return NextResponse.json(
      {
        error: 'Failed to fetch media assets',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
