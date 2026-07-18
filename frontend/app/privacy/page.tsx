import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Policy · Lyriq',
  description: 'Lyriq Privacy Policy',
};

export default function PrivacyPage() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-12 text-neutral-200">
      <div className="mb-8 border border-amber-800/60 bg-amber-950/30 rounded-lg p-4 text-amber-200 text-sm">
        <strong className="font-semibold">Draft.</strong> Adapted for
        Lyriq&apos;s current free, ad-free, no-account launch. Has <em>not</em>
        been reviewed by an attorney; have counsel review before scaling up.
      </div>

      <h1 className="text-4xl font-black text-white tracking-tight mb-2">
        Privacy Policy
      </h1>
      <p className="text-neutral-500 text-sm mb-10">Effective: 2026-07-13</p>

      <div className="space-y-8 text-sm leading-relaxed">

        <section>
          <h2 className="text-white text-lg font-bold mb-2">1. Summary</h2>
          <p>
            Lyriq is a hobby project. There are no accounts, no sign-ups, no
            passwords, no payments. We do not use analytics or advertising
            trackers. This page describes what limited information the Service
            does handle and why.
          </p>
        </section>

        <section>
          <h2 className="text-white text-lg font-bold mb-2">
            2. What We Collect
          </h2>
          <ul className="list-disc list-inside space-y-1 text-neutral-300">
            <li>
              <strong className="text-neutral-100">Song requests.</strong> The
              titles and artists you search for and analyze are sent to our
              backend and stored so we can serve the analysis to future visitors.
              These records do not include any information about you.
            </li>
            <li>
              <strong className="text-neutral-100">IP address (transient).</strong>{' '}
              Your IP is held in-memory on the backend for rate-limiting purposes
              (to prevent one visitor from exhausting our monthly AI budget). It
              is not written to a database and is discarded when the server
              restarts.
            </li>
            <li>
              <strong className="text-neutral-100">Standard server logs.</strong>{' '}
              Our host may keep short-term access logs (IP, request path,
              timestamp) for operational purposes. Retention depends on the host
              and is typically 7&ndash;30 days.
            </li>
          </ul>
          <p className="mt-2">
            We do not collect names, email addresses, phone numbers, locations,
            device fingerprints, or any other personally identifying data. We do
            not set advertising or analytics cookies.
          </p>
        </section>

        <section>
          <h2 className="text-white text-lg font-bold mb-2">
            3. Third-Party Services
          </h2>
          <p className="mb-2">
            When you analyze a song, the following third parties receive the
            song title and artist as part of the analysis pipeline. None of them
            receive your identity from us.
          </p>
          <div className="border border-neutral-800 rounded-lg overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-neutral-900 text-neutral-400 uppercase tracking-wider">
                <tr>
                  <th className="text-left px-3 py-2">Service</th>
                  <th className="text-left px-3 py-2">Purpose</th>
                  <th className="text-left px-3 py-2">Data sent</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800 text-neutral-300">
                <tr>
                  <td className="px-3 py-2">Anthropic (Claude)</td>
                  <td className="px-3 py-2">AI interpretation</td>
                  <td className="px-3 py-2">Song title, artist, lyrics</td>
                </tr>
                <tr>
                  <td className="px-3 py-2">Genius</td>
                  <td className="px-3 py-2">Lyrics, annotations</td>
                  <td className="px-3 py-2">Song title, artist</td>
                </tr>
                <tr>
                  <td className="px-3 py-2">Deezer</td>
                  <td className="px-3 py-2">Album + artist metadata</td>
                  <td className="px-3 py-2">Song title, artist</td>
                </tr>
                <tr>
                  <td className="px-3 py-2">YouTube</td>
                  <td className="px-3 py-2">Community comments</td>
                  <td className="px-3 py-2">Song title, artist</td>
                </tr>
                <tr>
                  <td className="px-3 py-2">Reddit</td>
                  <td className="px-3 py-2">Community discussion</td>
                  <td className="px-3 py-2">Song title, artist</td>
                </tr>
                <tr>
                  <td className="px-3 py-2">Supabase</td>
                  <td className="px-3 py-2">Persistent storage</td>
                  <td className="px-3 py-2">Analyzed song records</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="text-white text-lg font-bold mb-2">
            4. Browser Storage
          </h2>
          <p>
            Lyriq uses <span className="font-mono text-neutral-400">sessionStorage</span>{' '}
            in your browser to cache the most-recently-viewed song so navigating
            back to it feels instant. This data stays on your device, is not
            transmitted to us, and is cleared when you close the tab. Lyriq does
            not set tracking cookies.
          </p>
        </section>

        <section>
          <h2 className="text-white text-lg font-bold mb-2">
            5. Data Retention
          </h2>
          <ul className="list-disc list-inside space-y-1 text-neutral-300">
            <li>Analyzed song records are kept indefinitely (they are public artifacts and reused across visitors).</li>
            <li>IP addresses used for rate limiting are held in memory only and are lost on server restart.</li>
            <li>Server logs are retained per the host&apos;s default policy (typically 7&ndash;30 days).</li>
          </ul>
        </section>

        <section>
          <h2 className="text-white text-lg font-bold mb-2">6. Your Rights</h2>
          <p>
            Because Lyriq does not link data to individuals, there is no personal
            data to access, correct, or delete. If you believe an analyzed song
            record should be removed (for example, because it violates a
            copyright or contains content about you personally), see the DMCA /
            takedown section in the{' '}
            <a href="/terms" className="text-purple-400 hover:text-purple-300 underline underline-offset-2">
              Terms of Service
            </a>
            .
          </p>
        </section>

        <section>
          <h2 className="text-white text-lg font-bold mb-2">7. Children</h2>
          <p>
            Lyriq is not directed to children under 13. Because we collect no
            personal data, no special COPPA handling applies.
          </p>
        </section>

        <section>
          <h2 className="text-white text-lg font-bold mb-2">
            8. International Users
          </h2>
          <p>
            Our servers and processors operate in the United States. If you
            access the Service from outside the U.S., you understand that limited
            transient data (as described above) is processed in the U.S.
          </p>
        </section>

        <section>
          <h2 className="text-white text-lg font-bold mb-2">9. Security</h2>
          <p>
            We use standard measures (HTTPS, encrypted database connections) but
            no system is fully secure. Use the Service at your own risk.
          </p>
        </section>

        <section>
          <h2 className="text-white text-lg font-bold mb-2">10. Changes</h2>
          <p>
            We may revise this Policy. The &ldquo;Effective&rdquo; date above
            reflects the last revision. Continued use after changes constitutes
            acceptance.
          </p>
        </section>

        <section>
          <h2 className="text-white text-lg font-bold mb-2">11. Contact</h2>
          <p>
            Questions or requests:{' '}
            <span className="font-mono text-neutral-400">hello@lyriq.example</span>
          </p>
        </section>

      </div>
    </main>
  );
}
