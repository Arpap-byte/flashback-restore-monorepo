# 🔴 RAPPORT D'AUDIT COMPLET — FLASHBACK RESTORE

**Audit duo :** DeepSeek Pro (collecte terrain) + Claude Sonnet 4.6 (analyse critique)
**Date :** 12 Mai 2026
**Périmètre :** Backend (API, DB, code), Frontend (UX, SEO, accessibilité), Infrastructure (sécurité, déploiement), DevOps (git, CI/CD, secrets)

---

> ⚠️ **AVERTISSEMENT :** Ce produit, en l'état actuel, **ne doit pas être mis en production publique**. La surface d'attaque est critique, les secrets sont compromis, l'isolation des services est inexistante et plusieurs flux métier sont cassés.

---

## 📊 NOTE GLOBALE : 2.5/10

| Axe | Note | Avis Claude Sonnet |
|-----|------|-------------------|
| Sécurité | **1.5/10** | Secrets compromis, DB publique, TLS obsolète, zéro isolation, SSRF, rate limit bypass |
| Code & Architecture | **3/10** | Anti-patterns async, double pool DB, erreurs non gérées, bugs métier actifs |
| Modèle de données | **4/10** | Schéma cohérent mais contraintes incohérentes, indexes manquants, tokens en clair |
| Gestion Admin | **2.5/10** | Aucun dashboard opérationnel, monitoring absent, cleanup non fonctionnel |
| UX & Frontend | **3.5/10** | Flux de conversion cassé, SEO inexistant, accessibilité défaillante, navigation incohérente |
| Bonnes Pratiques | **2/10** | Secrets dans git, pas de CI/CD, pas de politique de sécurité, tests insuffisants |

---

## 🔥 TOP 10 ACTIONS PRIORITAIRES (P0 — Immédiat)

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| **1** | **Rotation de TOUS les secrets compromis** (Gemini x2, Stripe, D-ID, SMTP, JWT, admin, n8n) + purge git | Fraude financière, vol de données | 2h |
| **2** | **Fermer les ports 8000, 8001, 5432** et tous les ports superflus dans UFW | DB accessible depuis Internet, bypass auth | 30min |
| **3** | **Corriger le webhook Stripe** — vérifier la signature `stripe.Webhook.construct_event()` | Fraude : crédits gratuits, fausses souscriptions | 1h |
| **4** | **Sécuriser les fichiers** : `.env` en 600, `.env.bak` supprimé, `.gitignore` pour `.bak`, `uploads/` en 700 | Exfiltration de tous les secrets et photos utilisateurs | 1h |
| **5** | **Ajouter auth sur `/api/animate/{job_id}`** et endpoints Stripe | SSRF non authentifié, vol d'infos | 2h |
| **6** | **Activer TLS 1.2 minimum + headers sécurité** dans Traefik (HSTS, CSP, X-Frame-Options, X-Content-Type-Options) | Toutes les requêtes HTTPS sans aucune protection | 1h |
| **7** | **Réparer les boutons "S'abonner"** (flux de conversion Stripe) | Zéro revenu possible | 3h |
| **8** | **Isoler les services systemd** (User=flashback, NoNewPrivileges, ProtectSystem=strict) | Exploit applicatif = root immédiat | 2h |
| **9** | **Hasher les tokens de reset de mot de passe** (SHA-256 minimum) | Dump DB = prise de contrôle de tous les comptes | 1h |
| **10** | **Vérifier les crédits AVANT de traiter l'upload** dans `/api/analyze` | Utilisateurs sans crédits consomment des ressources | 1h |

---

## 🗂️ INVENTAIRE COMPLET DES BUGS (93 problèmes)

### P0 — CRITIQUES (25 bugs)

#### Secrets & Credentials (8)
| ID | Source | Description |
|----|--------|-------------|
| SEC-01 | Backend | `.env` en 644 avec TOUS les secrets en clair |
| SEC-02 | Backend | `.env.bak` non gitignoré avec secrets |
| SEC-03 | Backend | Clé Gemini commitée dans git (`.env.example`) |
| SEC-04 | Backend | Secrets en dur dans unit files systemd |
| SEC-05 | Backend | `config.py.bak` exposé |
| SEC-06 | Infra | Secrets n8n en dur (encryption key, license key) |
| SEC-07 | Infra | Docker compose backups avec secrets (.bak, .save) |
| SEC-08 | Backend | D-ID key = `email:password` en base64 (pas chiffré) |

#### Réseau & Exposition (7)
| ID | Source | Description |
|----|--------|-------------|
| NET-01 | Infra | Ports 8000 et 8001 ouverts monde entier — bypass Traefik auth |
| NET-02 | Infra | Port 5432 PostgreSQL exposé publiquement + credentials triviaux |
| NET-03 | Infra | Pas de headers sécurité via Traefik HTTPS (HSTS, CSP, X-Frame, etc.) |
| NET-04 | Infra | TLS 1.0 et 1.1 activés |
| NET-05 | Infra | Services systemd en root avec zéro isolation |
| NET-06 | Infra | Rate limiter bypass via `X-Forwarded-For` (confiance aveugle) |
| NET-07 | Infra | Docker socket exposé à Traefik (escalade root) |

#### Auth & Sessions (4)
| ID | Source | Description |
|----|--------|-------------|
| AUTH-01 | Backend | SSRF sur `GET /api/animate/{job_id}` — pas d'authentification |
| AUTH-02 | Backend | Endpoints Stripe sans JWT |
| AUTH-03 | Backend | JWT sans mécanisme de révocation |
| AUTH-04 | Backend | Webhook Stripe forgeable (pas de vérification de signature) |

#### Flux de conversion (3)
| ID | Source | Description |
|----|--------|-------------|
| UX-01 | Frontend | Boutons "S'abonner" inopérants — flux de conversion cassé |
| UX-02 | Frontend | AuthError console sur 100% des pages |
| UX-03 | Frontend | Validation formulaire auth inexistante (soumission à vide silencieuse) |

#### Rate Limiting (2)
| ID | Source | Description |
|----|--------|-------------|
| RL-01 | Backend | Décorateurs `@limiter.limit()` factices — ne font rien |
| RL-02 | Backend | Rate limiter mémoire non partagé entre workers |

#### Base de données (1)
| ID | Source | Description |
|----|--------|-------------|
| DB-01 | Backend | Credentials DB triviaux (`flashback:flashback`) |

---

### P1 — MAJEURS (28 bugs)

#### Backend
| ID | Description |
|----|-------------|
| B-01 | `nest_asyncio` appliqué globalement — anti-pattern async |
| B-02 | Double pool de connexions DB (async + sync legacy) |
| B-03 | Init DB confuse — `initialiser_base()` vs `init_db()` |
| B-04 | Tokens de reset stockés en clair dans `reinitialisation_mdp` |
| B-05 | Cache plan utilisateur sans invalidation (TTL 60s) |
| B-06 | Test unitaire incohérent (attend 409, code retourne 202) |
| B-07 | Endpoint Stripe subscription public (pas d'auth) |
| B-08 | Contrainte CHECK exclut "colorisation" → crash DB |
| B-09 | `cleanup` tente `os.remove()` sur URLs distantes |
| B-10 | `_vers_url()` incorrecte pour URLs externes |
| B-11 | `/api/analyze` consomme l'upload sans vérifier crédits |
| B-12 | Email synchrone dans route async (bloque event loop) |
| B-13 | Email send silencieux sur échec |
| B-14 | Validation MIME par Content-Type client (pas magic bytes) |
| B-15 | Auth D-ID potentiellement incorrecte |
| B-16 | Pas de pagination sur suppression totale |
| B-17 | Rate limiter ne couvre pas `/api/stripe/*`, `/api/admin/*`, `/api/colorize` |

#### Frontend
| ID | Description |
|----|-------------|
| UX-04 | Liens réseaux sociaux dead (`href="#"`) |
| UX-05 | "Mentions légales" = doublon de `/terms` (obligation légale FR) |
| UX-06 | URLs navbar vs footer incohérentes (`/restore` vs `/upload`) |
| UX-07 | Pas de navbar/footer sur pages auth et 404 |
| UX-08 | Inputs sans labels visibles (WCAG 2.1 AA) |
| UX-09 | Texte register vide |
| UX-10 | Toggle Connexion/Inscription cassé |

#### Infrastructure
| ID | Description |
|----|-------------|
| INF-01 | SQLite db `flashback.db` en 644 |
| INF-02 | `uploads/` 58 fichiers lisibles en 644 → RGPD |
| INF-03 | Pas de rate limiting Traefik |
| INF-04 | Fichiers `.bak` non gitignorés globalement |
| INF-05 | Ports superflus : 5678 (n8n), 3001, 4000, 11434 (Ollama), 5001-5002 |

---

### P2 — MODÉRÉS (25 bugs)

#### Backend
| ID | Description |
|----|-------------|
| B-18 | CORS `allow_methods=*` et `allow_headers=*` |
| B-19 | Headers sécurité insuffisants (manque CSP, Referrer-Policy, Permissions-Policy) |
| B-20 | Fuite d'erreurs brutes (stack traces, messages SQLAlchemy) |
| B-21 | `champ analyse=None type:ignore` — violation contrat Pydantic |
| B-22 | `/docs` Swagger public en production |
| B-23 | `register` avec valeurs hardcodées (`essais_restants: 3`) |
| B-24 | Email HTML sans version texte |
| B-25 | `load_dotenv` source confuse (`.env` racine vs `backend/.env`) |
| B-26 | Pas de vérification crédits avant `/api/analyze` (stockage gaspillé) |
| B-27 | `chemin_animation` vs `chemin_resultat` doublon potentiel |

#### Frontend
| ID | Description |
|----|-------------|
| UX-11 | Espace manquant "0€à vie" |
| UX-12 | "FlashbackRestore" sans espace dans logo footer |
| UX-13 | Titres H1 avec espaces manquants (5 pages) |
| UX-14 | Titre de page identique sur TOUTES les pages (SEO désastreux) |
| UX-15 | 404 sans navbar/footer + titre générique |
| UX-16 | `robots.txt` et `sitemap.xml` absents |
| UX-17 | Emails contact `.fr` vs `.com` incohérents |
| UX-18 | Accordéons FAQ non fonctionnels (questions 2-6) |
| UX-19 | Images before/after chargées en double |

#### Infrastructure
| ID | Description |
|----|-------------|
| INF-06 | Basic Auth sur site entier (acceptable pre-launch) |
| INF-07 | Headers sécu sur HTTP direct mais pas via HTTPS |
| INF-08 | `npx` sans version figée (supply chain) |
| INF-09 | `X-Powered-By: Next.js` exposé |

---

### P3 — MINEURS (15 bugs)

#### Backend
| ID | Description |
|----|-------------|
| B-28 | Pas de limite sur nom de fichier upload |
| B-29 | Pas de politique de mot de passe (min_length=8 seulement) |
| B-30 | Chemin `.env` non documenté |
| B-31 | Endpoint health trop bavard (expose versions, statuts connexions) |

#### Frontend
| ID | Description |
|----|-------------|
| UX-20 | "0 animation" grammaticalement incorrect |
| UX-21 | Cookie consent banner incohérent (absent sur /about, /privacy, etc.) |
| UX-22 | Liens CTA navigation client-side peu fiable |

#### Infrastructure
| ID | Description |
|----|-------------|
| INF-10 | Headers CORS redondants Traefik + FastAPI |
| INF-11 | Rate limits bas mais contournables |
| INF-12 | Pas de séparation des rôles DB (même compte pour tout) |

---

## 📋 PLAN DE CORRECTION PAR SÉVÉRITÉ

### 🔴 P0 — 5-8 jours (AVANT TOUT LANCEMENT)
- Rotation secrets + purge git (2h)
- Fermeture ports (30min)
- Webhook Stripe signature (1h)
- Permissions fichiers + .gitignore (1h)
- Auth endpoints manquants (2h)
- TLS 1.2+ + headers sécurité Traefik (1h)
- Boutons S'abonner (3h)
- Isolation systemd (2h)
- Hash reset tokens (1h)
- Vérifier crédits avant upload (1h)

### 🟠 P1 — 5-7 jours
- Supprimer `nest_asyncio`, unifier les pools DB
- Rate limiter Redis-based partagé
- Corriger la contrainte CHECK "colorisation"
- Corriger cleanup pour URLs distantes
- Tests unitaires cohérents
- Labels accessibilité + navigation auth/404
- Dead links réseaux sociaux
- URLs navbar vs footer unifiées

### 🟡 P2 — 5-7 jours
- Headers de sécurité complets
- Supprimer `/docs` en production
- Pages SEO : titres différenciés, robots.txt, sitemap.xml
- FAQ fonctionnelle
- Gestion d'erreurs propre (pas de stack traces brutes)
- Emails : async + version texte + log d'échec

### 🟢 P3 — 3-5 jours
- Politique de mot de passe
- Typos et grammaire
- Cookie consent cohérent
- Documentation architecture

---

## 🎯 RECOMMANDATIONS STRATÉGIQUES POUR LE LANCEMENT

1. **Ne pas lancer en production avant d'avoir traité au minimum tous les P0** — certains bugs (DB publique, secrets compromis) exposent à des risques légaux (RGPD) et financiers (Stripe)
2. **Mettre en place un pipeline CI/CD** — tests automatisés avant chaque déploiement, rollback automatique
3. **Séparer les environnements** — dev, staging, production avec des credentials distincts
4. **Audit RGPD** — les photos utilisateurs dans `uploads/` en 644 sont une violation
5. **Monitoring** — Prometheus + Grafana ou équivalent pour surveiller les jobs, les erreurs API, l'utilisation crédits
6. **Documenter l'architecture** — un nouveau développeur doit pouvoir comprendre la stack en 30 minutes
7. **Rate limiting Redis** — remplacer le rate limiter mémoire par une solution Redis partagée
8. **Plan de reprise d'activité** — backups DB automatisés, procédure de restauration documentée
