# Tech Talks with Manju — AI Careers

Website: https://aicareers.vrisama.in

This repository hosts the light-themed Tech Talks with Manju learning platform, including course previews, articles, AI tools, Mock Interview Studio, and a client-side Resume Builder.

## GitHub Pages setup

1. Go to **Settings → Pages**.
2. Set **Build and deployment** → **Deploy from a branch**, branch **main**, folder **/(root)**. Save.
3. Set **Custom domain** to `aicareers.vrisama.in` (also stored in the root `CNAME` file).
4. In GoDaddy DNS for `vrisama.in`, set: `CNAME` host `aicareers` → `mjeenugara9663.github.io`.
5. When certificate provisioning completes, enable **Enforce HTTPS**.

The root domain and other subdomains should remain unchanged.

## Launch limitations

Static frontend only. Enrollments and dashboard progress are browser-local demos, not registered student accounts. Resume Builder content remains in the visitor's browser; use privacy guidance before entering sensitive data. Mock Interview AI calls require provider access and should use a secure backend proxy before real user adoption. Payments and a production authentication service have not yet been set up. **Never commit provider API keys into this repository.**
