/**
 * Email Tracking Utilities
 *
 * Provides functions to inject tracking pixels, rewrite links for click tracking,
 * add UTM parameters, and generate unsubscribe links for email campaigns.
 */

export interface UTMParameters {
  utmSource?: string | null;
  utmMedium?: string | null;
  utmCampaign?: string | null;
  utmContent?: string | null;
}

/**
 * Main function to process HTML email content before sending
 * Injects tracking pixel, rewrites links, adds UTM parameters
 */
export function processEmailForSending(
  htmlContent: string,
  recipientId: string,
  baseUrl: string,
  utmParams?: UTMParameters
): string {
  let processedHtml = htmlContent;

  // Step 1: Replace unsubscribe link placeholder
  processedHtml = replaceUnsubscribePlaceholder(processedHtml, recipientId, baseUrl);

  // Step 2: Add UTM parameters to all links
  if (utmParams && hasUTMParams(utmParams)) {
    processedHtml = addUTMParametersToLinks(processedHtml, utmParams);
  }

  // Step 3: Rewrite links for click tracking
  processedHtml = rewriteLinksForTracking(processedHtml, recipientId, baseUrl);

  // Step 4: Inject tracking pixel
  processedHtml = injectTrackingPixel(processedHtml, recipientId, baseUrl);

  return processedHtml;
}

/**
 * Injects a 1x1 transparent tracking pixel before the closing </body> tag
 */
export function injectTrackingPixel(
  htmlContent: string,
  recipientId: string,
  baseUrl: string
): string {
  const trackingPixelUrl = `${baseUrl}/api/track/open/${recipientId}`;
  const trackingPixel = `<img src="${trackingPixelUrl}" width="1" height="1" alt="" style="display:none;" />`;

  // Insert before </body> if it exists, otherwise append to end
  if (htmlContent.includes('</body>')) {
    return htmlContent.replace('</body>', `${trackingPixel}</body>`);
  }

  return htmlContent + trackingPixel;
}

/**
 * Rewrites all <a href="..."> links to go through click tracking endpoint
 */
export function rewriteLinksForTracking(
  htmlContent: string,
  recipientId: string,
  baseUrl: string
): string {
  // Match all <a href="..."> tags
  const linkRegex = /<a\s+([^>]*\s+)?href=["']([^"']+)["']([^>]*)>/gi;

  return htmlContent.replace(linkRegex, (match, before = '', url, after = '') => {
    // Don't track the unsubscribe link (already tracking endpoint)
    if (url.includes('/api/unsubscribe/') || url.includes('/api/track/')) {
      return match;
    }

    // Don't track mailto: or tel: links
    if (url.startsWith('mailto:') || url.startsWith('tel:') || url.startsWith('#')) {
      return match;
    }

    // Create tracking URL
    const trackingUrl = `${baseUrl}/api/track/click/${recipientId}?url=${encodeURIComponent(url)}`;

    return `<a ${before}href="${trackingUrl}"${after}>`;
  });
}

/**
 * Adds UTM parameters to all HTTP/HTTPS links in the HTML
 */
export function addUTMParametersToLinks(
  htmlContent: string,
  utmParams: UTMParameters
): string {
  const linkRegex = /<a\s+([^>]*\s+)?href=["']([^"']+)["']([^>]*)>/gi;

  return htmlContent.replace(linkRegex, (match, before = '', url, after = '') => {
    // Only add UTM to http/https links
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      return match;
    }

    // Don't add UTM to unsubscribe or tracking links
    if (url.includes('/api/unsubscribe/') || url.includes('/api/track/')) {
      return match;
    }

    const urlWithUTM = addUTMToURL(url, utmParams);
    return `<a ${before}href="${urlWithUTM}"${after}>`;
  });
}

/**
 * Adds UTM parameters to a single URL
 */
export function addUTMToURL(url: string, utmParams: UTMParameters): string {
  try {
    const urlObj = new URL(url);

    if (utmParams.utmSource) {
      urlObj.searchParams.set('utm_source', utmParams.utmSource);
    }
    if (utmParams.utmMedium) {
      urlObj.searchParams.set('utm_medium', utmParams.utmMedium);
    }
    if (utmParams.utmCampaign) {
      urlObj.searchParams.set('utm_campaign', utmParams.utmCampaign);
    }
    if (utmParams.utmContent) {
      urlObj.searchParams.set('utm_content', utmParams.utmContent);
    }

    return urlObj.toString();
  } catch (error) {
    // Invalid URL, return as-is
    console.error('Failed to add UTM parameters to URL:', url, error);
    return url;
  }
}

/**
 * Replaces {{unsubscribe_link}} placeholder with actual unsubscribe URL
 */
export function replaceUnsubscribePlaceholder(
  htmlContent: string,
  recipientId: string,
  baseUrl: string
): string {
  const unsubscribeUrl = generateUnsubscribeLink(recipientId, baseUrl);
  return htmlContent.replace(/\{\{unsubscribe_link\}\}/g, unsubscribeUrl);
}

/**
 * Generates an unsubscribe link for a recipient
 */
export function generateUnsubscribeLink(recipientId: string, baseUrl: string): string {
  return `${baseUrl}/api/unsubscribe/${recipientId}`;
}

/**
 * Checks if any UTM parameters are provided
 */
function hasUTMParams(utmParams: UTMParameters): boolean {
  return !!(
    utmParams.utmSource ||
    utmParams.utmMedium ||
    utmParams.utmCampaign ||
    utmParams.utmContent
  );
}

/**
 * Strips HTML tags from text (used for plain text fallback)
 */
export function stripHTMLTags(html: string): string {
  return html.replace(/<[^>]*>/g, '');
}
