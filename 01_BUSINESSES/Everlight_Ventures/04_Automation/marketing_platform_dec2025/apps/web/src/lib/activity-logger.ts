/**
 * Activity Logger Utility
 *
 * Provides a centralized function to log activities without throwing errors.
 * This ensures logging failures don't break the application.
 */

import { prisma } from '@everlight/db';
import { ActivityType } from '@prisma/client';

interface LogActivityParams {
  type: ActivityType;
  projectId?: string | null;
  userId?: string | null;
  metadata?: Record<string, any> | null;
}

/**
 * Logs an activity to the database
 * Never throws - logging failures are logged to console only
 */
export async function logActivity({
  type,
  projectId,
  userId,
  metadata,
}: LogActivityParams): Promise<void> {
  try {
    await prisma.activity.create({
      data: {
        type,
        projectId: projectId || null,
        userId: userId || null,
        metadata: metadata || null,
      },
    });

    console.log('[Activity Log]', {
      type,
      projectId,
      userId,
      metadata,
    });
  } catch (error) {
    // Never throw - logging shouldn't break the app
    console.error('[Activity Log] Failed to log activity:', error);
    console.error('[Activity Log] Activity details:', {
      type,
      projectId,
      userId,
      metadata,
    });
  }
}
