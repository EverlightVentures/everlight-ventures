/**
 * Facebook OAuth - Connect Initiation
 * Initiates the OAuth flow for connecting Facebook/Instagram accounts
 */

import { NextRequest, NextResponse } from 'next/server';
import { generateFacebookOAuthUrl } from '@/lib/social-media/facebook-client';
import prisma from '@/lib/prisma';
import crypto from 'crypto';

/**
 * GET /api/social/facebook/connect?projectSlug=xxx
 * Initiate Facebook OAuth flow
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const projectSlug = searchParams.get('projectSlug');

    if (!projectSlug) {
      return NextResponse.json(
        { error: 'Project slug is required' },
        { status: 400 }
      );
    }

    // Verify project exists
    const project = await prisma.project.findUnique({
      where: { slug: projectSlug },
    });

    if (!project) {
      return NextResponse.json(
        { error: 'Project not found' },
        { status: 404 }
      );
    }

    // Get Facebook app credentials from environment
    const appId = process.env.FACEBOOK_APP_ID;
    const appSecret = process.env.FACEBOOK_APP_SECRET;

    if (!appId || !appSecret) {
      return NextResponse.json(
        {
          error: 'Facebook app credentials not configured',
          message:
            'Please set FACEBOOK_APP_ID and FACEBOOK_APP_SECRET in your environment variables',
        },
        { status: 500 }
      );
    }

    // Generate state token for CSRF protection
    const state = crypto.randomBytes(32).toString('hex');

    // Store state in session or database (for now, we'll include it in the callback)
    // In production, you'd want to store this in a session or Redis
    const stateData = {
      projectSlug,
      timestamp: Date.now(),
    };

    // For development, we'll encode the project slug in the state
    const encodedState = Buffer.from(JSON.stringify(stateData)).toString('base64');

    // Generate OAuth URL
    const redirectUri = `${process.env.NEXTAUTH_URL}/api/social/facebook/callback`;

    const oauthUrl = generateFacebookOAuthUrl(
      {
        appId,
        appSecret,
        redirectUri,
      },
      encodedState
    );

    // Redirect to Facebook OAuth
    return NextResponse.redirect(oauthUrl);
  } catch (error) {
    console.error('[Facebook Connect] Error:', error);
    return NextResponse.json(
      {
        error: 'Failed to initiate Facebook connection',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
