Tu es un auditeur senior indépendant. Tu audites le SaaS Flashback Restore (restauration de photos par IA, https://flashback-restore.com). Le site est en pre-launch, protégé par HTTP Basic Auth.

## CONTEXTE TECHNIQUE

**Stack:** FastAPI (Python) backend :8000, Next.js 16 (Turbopack) frontend :8001, PostgreSQL 16, Traefik v3 reverse proxy, Redis, Stripe, Gemini API, D-ID API
**Déploiement:** VPS Hostinger Ubuntu, services systemd (root), Docker pour Traefik/DB
**Auth:** NextAuth.js JWT + email/password legacy, HTTP Basic Auth pre-launch
**Modèle de données:** 7 tables (utilisateurs, travaux, abonnements, essais_gratuits, achats_credits, consommation_credits, reinitialisation_mdp, audit_logs) + migration récente avec 5 nouvelles colonnes (retention_jours, derniere_activite, chemin_animation, taille_original, taille_resultat)

## BUGS DÉTECTÉS PAR L'AUDIT BACKEND (36 bugs)

P0 (6): Secrets en clair dans .env, .env.bak non gitignoré, credentials DB triviaux, load_dotenv source confuse, config.py.bak exposé, webhook Stripe forgeable
P1 (12): SSRF sur /api/animate/{job_id} sans auth, endpoints Stripe sans JWT, rate limiter mémoire non partagé entre workers, decorateurs rate limit factices, test unitaire incohérent, JWT sans révocation, nest_asyncio global, double pool DB, init DB confuse, tokens reset stockés en clair, cache plan sans invalidation
P2 (12): CORS trop permissif, headers sécurité insuffisants, contrainte CHECK exclut "colorisation", cleanup tente os.remove sur URLs distantes, fuite erreurs brutes, /api/analyze consomme l'upload sans vérifier crédits, email send silencieux, email synchrone dans route async, pas de pagination suppression totale, _vers_url incorrecte pour URLs externes, auth D-ID incorrecte, validation MIME par Content-Type client
P3 (6): Pas de limite nom fichier, pas de politique mot de passe, champ analyse=None type:ignore, register valeurs hardcodées, email HTML sans version texte, chemin .env non documenté

## BUGS DÉTECTÉS PAR L'AUDIT FRONTEND/UX (22 bugs)

P0 (3): AuthError console sur 100% des pages, validation formulaire auth inexistante, boutons S'abonner inopérants (flux conversion cassé)
P1 (7): Liens réseaux sociaux dead (#), Mentions légales = doublon /terms, URLs navbar vs footer incohérentes, pas de navbar/footer sur auth/404, inputs sans labels visibles, texte register vide, toggle Connexion/Inscription cassé
P2 (7): Espace manquant "0€à vie", "FlashbackRestore" sans espace, titres H1 avec espaces manquants (5 pages), titre de page identique partout, 404 sans navbar, robots.txt/sitemap.xml absents, emails de contact .fr vs .com
P3 (5): Images before/after en double, accordéons FAQ non fonctionnels, "0 animation" grammaticalement incorrect, cookie banner incohérent, liens CTA navigation client-side peu fiable

## BUGS DÉTECTÉS PAR L'AUDIT SÉCURITÉ/INFRA (35 findings)

P0 (16): Pas de headers sécurité via Traefik HTTPS, TLS 1.0/1.1 activés, services systemd en root avec zéro isolation, secrets en dur dans unit file systemd, ports 8000/8001 ouverts monde entier (bypass auth), DB PostgreSQL port 5432 exposé, .env lisible 644, .env.bak non gitignoré, rate limiter bypass via X-Forwarded-For, clé Gemini commitée dans git (.env.example), secrets n8n en dur (encryption key, license key)
P1 (9): Pas de rate limiting Traefik, SQLite db lisible 644, uploads/ 58 fichiers lisibles, D-ID key encodée email:password, docker-compose backups avec secrets, .bak non gitignorés, Docker socket exposé à Traefik, ports superflus 5678/3001/4000/11434/5001-5002
P2 (6): Basic auth sur site entier, headers sécu sur HTTP direct mais pas HTTPS, /docs public, CORS allow_methods/headers *, npx sans version figée, EmailStr introuvable (problème déjà corrigé?)
P3 (4): Headers CORS redondants, X-Powered-By Next.js exposé, rate limits bas, health endpoint bavard

## TA MISSION

Produis un rapport d'audit structuré et SÉVÈRE couvrant 6 axes :

1. **SÉCURITÉ** /10 — Secrets, auth, isolation, surface d'attaque, headers, TLS
2. **CODE & ARCHITECTURE** /10 — Qualité du code, patterns, DRY, gestion d'erreurs, async/sync, duplication
3. **MODÈLE DE DONNÉES** /10 — Schéma, contraintes, indexes, types, cohérence avec le code
4. **GESTION ADMIN** /10 — Dashboard, monitoring, logs, cleanup, droits, audit trail
5. **UX & FRONTEND** /10 — Navigation, formulaires, accessibilité, responsive, SEO, performances
6. **BONNES PRATIQUES** /10 — DevSecOps, git, CI/CD, docs, tests, qualité

Puis :
- **NOTE GLOBALE** /10
- **TOP 10 ACTIONS PRIORITAIRES** (P0 immédiat)
- **PLAN DE CORRECTION** par sévérité (P0/P1/P2/P3) avec effort estimé
- **RECOMMANDATIONS STRATÉGIQUES** pour le lancement

Sois SÉVÈRE, PRÉCIS, et OPÉRATIONNEL. Ne félicite pas. Ne dis pas "c'est bien". Cherche ce qui peut casser.
