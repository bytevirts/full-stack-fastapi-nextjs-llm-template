{%- if cookiecutter.enable_i18n %}
import createMiddleware from 'next-intl/middleware';
import { locales, defaultLocale } from './i18n';

export default createMiddleware({
  // A list of all locales that are supported
  locales,

  // Used when no locale matches
  defaultLocale,

  // Prefix the default locale (e.g., /en/about instead of /about)
  localePrefix: 'always',
});

export const config = {
  // Match only internationalized pathnames
  matcher: [
    // Match all pathnames except for
    // - /api (API routes)
    // - /_next (Next.js internals)
    // - /static (inside /public)
    // - /_vercel (Vercel internals)
    // - All root files like favicon.ico, robots.txt, etc.
    '/((?!api|_next|_vercel|static|.*\\..*).*)',
    // However, match all pathnames within `/api`, except for webhooks
    // '/api/((?!webhooks).*)',
  ],
};
{%- else %}
// Middleware is disabled when i18n is not enabled
export { };
{%- endif %}
