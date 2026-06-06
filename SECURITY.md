# Security

## Reporting A Vulnerability

Please report security issues privately to the maintainers instead of opening a public GitHub issue. Include the affected version, reproduction steps, and potential impact.

## API Keys

- Never commit OpenAI API keys or other secrets.
- Prefer the `OPENAI_API_KEY` environment variable for persistent local use.
- The local testing UI binds to `127.0.0.1`, does not save entered keys, and clears its key field after submission.
- Revoke and replace any key that appears in chat, screenshots, logs, shell history, or commits.

## Camera Privacy

- Camera frames are written locally under `.camera-mcp/frames/` by default.
- `.camera-mcp/`, `cameras.json`, and generated OpenClaw configuration are excluded from Git.
- Review captured frames before sharing logs, bug reports, or screenshots.
- Keep the local testing UI bound to `127.0.0.1` unless you add authentication and understand the exposure.
