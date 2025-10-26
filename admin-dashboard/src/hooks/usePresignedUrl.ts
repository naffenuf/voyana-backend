import { useState, useEffect } from 'react';
import { mediaApi } from '../lib/api';

/**
 * Hook to automatically presign S3 URLs for display
 * @param url - The original URL (may be S3 or public URL)
 * @returns The presigned URL (or original if not S3)
 */
export function usePresignedUrl(url: string | null | undefined): string | null {
  const [presignedUrl, setPresignedUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!url) {
      setPresignedUrl(null);
      return;
    }

    // If it's not an S3 URL, use it directly
    if (!url.includes('s3.amazonaws.com') && !url.includes('.s3.')) {
      setPresignedUrl(url);
      return;
    }

    // Presign S3 URLs
    let isMounted = true;
    setLoading(true);

    mediaApi
      .getPresignedUrl(url)
      .then((signed) => {
        if (isMounted) {
          setPresignedUrl(signed);
          setLoading(false);
        }
      })
      .catch((error) => {
        console.error('Failed to presign URL:', error);
        if (isMounted) {
          setPresignedUrl(null);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [url]);

  return loading ? null : presignedUrl;
}

/**
 * Hook to presign multiple URLs at once
 * @param urls - Array of URLs to presign
 * @returns Array of presigned URLs (in same order)
 */
export function usePresignedUrls(urls: (string | null | undefined)[]): (string | null)[] {
  const [presignedUrls, setPresignedUrls] = useState<(string | null)[]>([]);

  useEffect(() => {
    let isMounted = true;

    const presignAll = async () => {
      const results = await Promise.all(
        urls.map(async (url) => {
          if (!url) return null;

          // If it's not an S3 URL, use it directly
          if (!url.includes('s3.amazonaws.com') && !url.includes('.s3.')) {
            return url;
          }

          try {
            return await mediaApi.getPresignedUrl(url);
          } catch (error) {
            console.error('Failed to presign URL:', error);
            return null;
          }
        })
      );

      if (isMounted) {
        setPresignedUrls(results);
      }
    };

    presignAll();

    return () => {
      isMounted = false;
    };
  }, [JSON.stringify(urls)]);

  return presignedUrls;
}
