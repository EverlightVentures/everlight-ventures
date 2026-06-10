import { NextAuthOptions } from 'next-auth';
import { PrismaAdapter } from '@next-auth/prisma-adapter';
import CredentialsProvider from 'next-auth/providers/credentials';
import EmailProvider from 'next-auth/providers/email';
import { prisma } from '@everlight/db';
import { compare } from 'bcryptjs';
import { Resend } from 'resend';

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma),
  session: {
    strategy: 'jwt',
  },
  pages: {
    signIn: '/auth/signin',
    signOut: '/auth/signout',
    error: '/auth/error',
  },
  providers: [
    CredentialsProvider({
      name: 'credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }

        const user = await prisma.user.findUnique({
          where: { email: credentials.email },
        });

        if (!user || !user.passwordHash) {
          return null;
        }

        const isPasswordValid = await compare(
          credentials.password,
          user.passwordHash
        );

        if (!isPasswordValid) {
          return null;
        }

        return {
          id: user.id,
          email: user.email,
          name: user.name,
        };
      },
    }),
    EmailProvider({
      from: process.env.EMAIL_FROM || 'noreply@everlight.dev',
      async sendVerificationRequest({ identifier: email, url }) {
        // For dev mode, just log the magic link
        if (process.env.NODE_ENV === 'development') {
          console.log('Magic link for', email, ':', url);
          return;
        }

        // Send email via Resend
        const resend = new Resend(process.env.RESEND_API_KEY);

        try {
          await resend.emails.send({
            from: process.env.EMAIL_FROM || 'noreply@everlight.dev',
            to: email,
            subject: 'Sign in to Everlight Ventures',
            html: `
              <!DOCTYPE html>
              <html>
                <head>
                  <meta charset="utf-8">
                  <meta name="viewport" content="width=device-width, initial-scale=1.0">
                </head>
                <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                  <div style="background-color: #f8f9fa; border-radius: 8px; padding: 30px; margin: 20px 0;">
                    <h1 style="color: #1a1a1a; margin-top: 0;">Sign in to Everlight Ventures</h1>
                    <p style="font-size: 16px; color: #666; margin: 20px 0;">Click the button below to sign in to your account:</p>
                    <a href="${url}" style="display: inline-block; background-color: #0070f3; color: white; text-decoration: none; padding: 12px 30px; border-radius: 6px; font-weight: 600; margin: 20px 0;">Sign In</a>
                    <p style="font-size: 14px; color: #999; margin-top: 30px;">If you didn't request this email, you can safely ignore it.</p>
                    <p style="font-size: 12px; color: #ccc; margin-top: 20px; border-top: 1px solid #e0e0e0; padding-top: 20px;">This link will expire in 24 hours.</p>
                  </div>
                </body>
              </html>
            `,
            text: `Sign in to Everlight Ventures\n\nClick the link below to sign in:\n\n${url}\n\nIf you didn't request this email, you can safely ignore it.\n\nThis link will expire in 24 hours.`,
          });

          console.log('Magic link email sent to', email);
        } catch (error) {
          console.error('Failed to send magic link email:', error);
          throw error;
        }
      },
    }),
  ],
  callbacks: {
    async session({ session, token }) {
      if (token && session.user) {
        session.user.id = token.sub!;
      }
      return session;
    },
    async jwt({ token, user }) {
      if (user) {
        token.sub = user.id;
      }
      return token;
    },
  },
};
