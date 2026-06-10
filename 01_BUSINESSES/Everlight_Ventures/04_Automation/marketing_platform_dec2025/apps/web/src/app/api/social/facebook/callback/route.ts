/**
 * Facebook OAuth - Callback Handler
 * Handles OAuth callback, exchanges code for tokens, and stores credentials
 */

import { NextRequest, NextResponse } from 'next/server';
import {
  exchangeCodeForToken,
  getLongLivedToken,
  getUserPages,
  getInstagramAccount,
  getInstagramProfile,
} from '@/lib/social-media/facebook-client';
import { encryptTokenData } from '@/lib/social-media/encryption';
import { logActivity } from '@/lib/activity-logger';
import prisma from '@/lib/prisma';

/**
 * GET /api/social/facebook/callback
 * Handle Facebook OAuth callback
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');
    const errorDescription = searchParams.get('error_description');

    // Handle OAuth errors
    if (error) {
      return NextResponse.redirect(
        `${process.env.NEXTAUTH_URL}/error?message=${encodeURIComponent(
          errorDescription || 'Facebook authorization failed'
        )}`
      );
    }

    if (!code || !state) {
      return NextResponse.redirect(
        `${process.env.NEXTAUTH_URL}/error?message=${encodeURIComponent(
          'Missing authorization code or state'
        )}`
      );
    }

    // Decode state to get project slug
    let projectSlug: string;
    try {
      const stateData = JSON.parse(Buffer.from(state, 'base64').toString());
      projectSlug = stateData.projectSlug;

      // Verify state timestamp (should be recent)
      const stateAge = Date.now() - stateData.timestamp;
      if (stateAge > 10 * 60 * 1000) {
        // 10 minutes
        throw new Error('State token expired');
      }
    } catch (err) {
      return NextResponse.redirect(
        `${process.env.NEXTAUTH_URL}/error?message=${encodeURIComponent(
          'Invalid state token'
        )}`
      );
    }

    // Get project
    const project = await prisma.project.findUnique({
      where: { slug: projectSlug },
    });

    if (!project) {
      return NextResponse.redirect(
        `${process.env.NEXTAUTH_URL}/error?message=${encodeURIComponent(
          'Project not found'
        )}`
      );
    }

    // Get Facebook app credentials
    const appId = process.env.FACEBOOK_APP_ID;
    const appSecret = process.env.FACEBOOK_APP_SECRET;

    if (!appId || !appSecret) {
      return NextResponse.redirect(
        `${process.env.NEXTAUTH_URL}/error?message=${encodeURIComponent(
          'Facebook app not configured'
        )}`
      );
    }

    const config = {
      appId,
      appSecret,
      redirectUri: `${process.env.NEXTAUTH_URL}/api/social/facebook/callback`,
    };

    // Exchange code for access token
    const tokenResponse = await exchangeCodeForToken(code, config);

    // Get long-lived token
    const longLivedToken = await getLongLivedToken(tokenResponse.accessToken, config);

    // Get user's Facebook Pages
    const pages = await getUserPages(longLivedToken.accessToken);

    if (pages.length === 0) {
      return NextResponse.redirect(
        `${process.env.NEXTAUTH_URL}/error?message=${encodeURIComponent(
          'No Facebook Pages found. Please create a Facebook Page first.'
        )}`
      );
    }

    // Use the first page (in production, let user select)
    const page = pages[0];

    // Encrypt and store Facebook Page credentials
    const encryptedTokens = encryptTokenData({
      accessToken: page.accessToken,
    });

    const facebookAccount = await prisma.socialMediaAccount.create({
      data: {
        platform: 'FACEBOOK',
        platformUserId: page.id,
        platformUsername: page.name,
        displayName: page.name,
        accessToken: encryptedTokens.accessToken,
        status: 'CONNECTED',
        lastSyncedAt: new Date(),
        projectId: project.id,
      },
    });

    // Log activity
    await logActivity({
      type: 'SOCIAL_ACCOUNT_CONNECTED',
      projectId: project.id,
      metadata: {
        platform: 'FACEBOOK',
        accountName: page.name,
      },
    });

    // Check for connected Instagram Business Account
    try {
      const igAccount = await getInstagramAccount(page.id, page.accessToken);

      if (igAccount) {
        // Get Instagram profile info
        const igProfile = await getInstagramProfile(igAccount.id, page.accessToken);

        // Encrypt and store Instagram credentials
        const encryptedIGTokens = encryptTokenData({
          accessToken: page.accessToken, // Uses same page access token
        });

        await prisma.socialMediaAccount.create({
          data: {
            platform: 'INSTAGRAM',
            platformUserId: igAccount.id,
            platformUsername: igProfile.username,
            displayName: igProfile.name || igProfile.username,
            profileImageUrl: igProfile.profilePictureUrl,
            accessToken: encryptedIGTokens.accessToken,
            status: 'CONNECTED',
            lastSyncedAt: new Date(),
            projectId: project.id,
          },
        });

        // Log Instagram connection
        await logActivity({
          type: 'SOCIAL_ACCOUNT_CONNECTED',
          projectId: project.id,
          metadata: {
            platform: 'INSTAGRAM',
            accountName: igProfile.username,
          },
        });
      }
    } catch (igError) {
      console.error('[Instagram Connection] Error:', igError);
      // Don't fail the whole flow if Instagram connection fails
    }

    // Redirect to settings page with success message
    return NextResponse.redirect(
      `${process.env.NEXTAUTH_URL}/projects/${projectSlug}/settings/social-media?success=true`
    );
  } catch (error) {
    console.error('[Facebook Callback] Error:', error);

    let errorMessage = 'Failed to connect Facebook account';
    if (error instanceof Error) {
      errorMessage += `: ${error.message}`;
    }

    return NextResponse.redirect(
      `${process.env.NEXTAUTH_URL}/error?message=${encodeURIComponent(errorMessage)}`
    );
  }
}
